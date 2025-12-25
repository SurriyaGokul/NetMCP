from typing import Dict, List, Optional
import json
from .audit_log import log_validation_test

OPTIMIZATION_PROFILES = {
    "gaming": "gaming",
    "streaming": "streaming", 
    "video_calls": "video_calls",
    "bulk_transfer": "bulk_transfer",
    "server": "server",
    "balanced": "balanced",
    
    # Legacy aliases for backward compatibility
    "throughput": "streaming",  # Legacy: throughput → streaming
}


class ValidationEngine:
    @staticmethod
    def validate_gaming_profile(before: Dict, after: Dict) -> Dict:
        """
        Validate changes for gaming workload.
        
        Gaming priorities:
        1. Latency reduction (40% weight) - CRITICAL
        2. Jitter reduction (30% weight) - VERY IMPORTANT
        3. Packet loss reduction (20% weight) - IMPORTANT
        4. Throughput stability (10% weight) - NICE TO HAVE
        
        Args:
            before: Benchmark results before changes
            after: Benchmark results after changes
        
        Returns:
            {
                "decision": "KEEP" | "ROLLBACK" | "UNCERTAIN",
                "score": int (0-100),
                "reasons": [str],
                "metrics_comparison": {...}
            }
        """
        score = 0
        reasons = []
        metrics = {}
        
        # Extract latency metrics
        before_lat = before.get("tests", {}).get("latency", {})
        after_lat = after.get("tests", {}).get("latency", {})
        
        if not before_lat.get("available") or not after_lat.get("available"):
            return {
                "decision": "UNCERTAIN",
                "score": 0,
                "reasons": ["Latency tests not available for comparison"],
                "metrics_comparison": {}
            }
        
        # 1. Average Latency (40% weight)
        before_avg = before_lat["avg_ms"]
        after_avg = after_lat["avg_ms"]
        latency_change = after_avg - before_avg
        latency_change_pct = (latency_change / before_avg) * 100 if before_avg > 0 else 0
        
        if after_avg < before_avg * 0.95:  # 5%+ improvement
            improvement = before_avg - after_avg
            score += 40
            reasons.append(f"✓ EXCELLENT: Latency improved by {improvement:.2f}ms ({abs(latency_change_pct):.1f}%)")
        elif after_avg < before_avg * 0.98:  # 2-5% improvement
            improvement = before_avg - after_avg
            score += 30
            reasons.append(f"✓ GOOD: Latency improved by {improvement:.2f}ms ({abs(latency_change_pct):.1f}%)")
        elif after_avg <= before_avg * 1.02:  # Within 2% (neutral)
            score += 20
            reasons.append(f"≈ NEUTRAL: Latency unchanged ({latency_change:+.2f}ms, {latency_change_pct:+.1f}%)")
        elif after_avg <= before_avg * 1.05:  # 2-5% worse
            score -= 20
            reasons.append(f"⚠ CAUTION: Latency slightly worse by {abs(latency_change):.2f}ms ({latency_change_pct:+.1f}%)")
        else:  # >5% worse
            score -= 40
            reasons.append(f"✗ BAD: Latency WORSENED by {abs(latency_change):.2f}ms ({latency_change_pct:+.1f}%)")
        
        metrics["latency_before_ms"] = before_avg
        metrics["latency_after_ms"] = after_avg
        metrics["latency_change_ms"] = latency_change
        metrics["latency_change_percent"] = latency_change_pct
        
        # 2. Jitter / Variability (30% weight)
        before_jitter = before_lat["jitter_ms"]
        after_jitter = after_lat["jitter_ms"]
        jitter_change = after_jitter - before_jitter
        jitter_change_pct = (jitter_change / before_jitter) * 100 if before_jitter > 0 else 0
        
        if after_jitter < before_jitter * 0.90:  # 10%+ improvement
            score += 30
            reasons.append(f"✓ Jitter reduced by {abs(jitter_change):.2f}ms ({abs(jitter_change_pct):.1f}%)")
        elif after_jitter < before_jitter * 0.95:  # 5-10% improvement
            score += 20
            reasons.append(f"✓ Jitter slightly reduced by {abs(jitter_change):.2f}ms")
        elif after_jitter <= before_jitter * 1.10:  # Within 10% (acceptable)
            score += 10
            reasons.append(f"≈ Jitter stable ({jitter_change:+.2f}ms)")
        elif after_jitter <= before_jitter * 1.25:  # 10-25% worse
            score -= 20
            reasons.append(f"⚠ Jitter increased by {abs(jitter_change):.2f}ms")
        else:  # >25% worse
            score -= 30
            reasons.append(f"✗ Jitter SIGNIFICANTLY WORSE (+{abs(jitter_change):.2f}ms)")
        
        metrics["jitter_before_ms"] = before_jitter
        metrics["jitter_after_ms"] = after_jitter
        metrics["jitter_change_ms"] = jitter_change
        
        # 3. Packet Loss (20% weight)
        before_loss = before_lat.get("packet_loss_percent", 0)
        after_loss = after_lat.get("packet_loss_percent", 0)
        loss_change = after_loss - before_loss
        
        if after_loss < before_loss and after_loss < 1.0:  # Reduced and minimal
            score += 20
            reasons.append(f"✓ Packet loss reduced: {before_loss:.1f}% → {after_loss:.1f}%")
        elif after_loss == before_loss and after_loss < 1.0:  # Stable and minimal
            score += 15
            reasons.append(f"✓ Packet loss stable at {after_loss:.1f}%")
        elif after_loss <= before_loss * 1.5 and after_loss < 2.0:  # Slight increase but acceptable
            score += 5
            reasons.append(f"≈ Packet loss: {before_loss:.1f}% → {after_loss:.1f}%")
        elif after_loss > 2.0:  # High packet loss
            score -= 20
            reasons.append(f"✗ HIGH packet loss: {after_loss:.1f}%")
        else:  # Increased loss
            score -= 15
            reasons.append(f"⚠ Packet loss increased: {before_loss:.1f}% → {after_loss:.1f}%")
        
        metrics["packet_loss_before_pct"] = before_loss
        metrics["packet_loss_after_pct"] = after_loss
        metrics["packet_loss_change"] = loss_change
        
        # 4. Connection Time (10% weight) - if available
        before_conn = before.get("tests", {}).get("connection_time", {})
        after_conn = after.get("tests", {}).get("connection_time", {})
        
        if before_conn.get("available") and after_conn.get("available"):
            before_conn_time = before_conn["avg_connect_ms"]
            after_conn_time = after_conn["avg_connect_ms"]
            conn_change = after_conn_time - before_conn_time
            
            if after_conn_time < before_conn_time * 0.9:
                score += 10
                reasons.append(f"✓ Connection time improved: {abs(conn_change):.2f}ms faster")
            elif after_conn_time <= before_conn_time * 1.1:
                score += 5
                reasons.append(f"≈ Connection time stable")
            else:
                score -= 5
                reasons.append(f"⚠ Connection time slower: +{abs(conn_change):.2f}ms")
            
            metrics["connection_before_ms"] = before_conn_time
            metrics["connection_after_ms"] = after_conn_time
            metrics["connection_change_ms"] = conn_change
        
        # Decision logic
        if score >= 60:
            decision = "KEEP"
            summary = f"Changes significantly improved gaming performance (score: {score}/100)"
        elif score >= 40:
            decision = "KEEP"
            summary = f"Changes moderately improved performance (score: {score}/100)"
        elif score >= 20:
            decision = "UNCERTAIN"
            summary = f"Changes had mixed results (score: {score}/100) - review metrics"
        elif score >= 0:
            decision = "UNCERTAIN"
            summary = f"Changes showed minimal benefit (score: {score}/100) - consider rollback"
        elif score >= -20:
            decision = "ROLLBACK"
            summary = f"Changes degraded performance (score: {score}/100) - rollback recommended"
        else:
            decision = "ROLLBACK"
            summary = f"Changes SIGNIFICANTLY degraded performance (score: {score}/100) - ROLLBACK IMMEDIATELY"
        
        return {
            "decision": decision,
            "score": score,
            "summary": summary,
            "reasons": reasons,
            "metrics_comparison": metrics
        }
    
    @staticmethod
    def validate_throughput_profile(before: Dict, after: Dict) -> Dict:
        """
        Validate changes for throughput-focused workload.
        
        Throughput priorities:
        1. Bandwidth increase (50% weight)
        2. Latency stability (20% weight)
        3. Retransmit reduction (20% weight)
        4. Connection stability (10% weight)
        """
        score = 0
        reasons = []
        metrics = {}
        
        # 1. Throughput (50% weight)
        before_tp = before.get("tests", {}).get("throughput", {})
        after_tp = after.get("tests", {}).get("throughput", {})
        
        if before_tp.get("available") and after_tp.get("available"):
            before_mbps = before_tp["throughput_mbps"]
            after_mbps = after_tp["throughput_mbps"]
            tp_change = after_mbps - before_mbps
            tp_change_pct = (tp_change / before_mbps) * 100 if before_mbps > 0 else 0
            
            if after_mbps > before_mbps * 1.10:  # 10%+ improvement
                score += 50
                reasons.append(f"✓ EXCELLENT: Throughput increased by {tp_change:.2f} Mbps ({tp_change_pct:.1f}%)")
            elif after_mbps > before_mbps * 1.05:  # 5-10% improvement
                score += 40
                reasons.append(f"✓ GOOD: Throughput increased by {tp_change:.2f} Mbps ({tp_change_pct:.1f}%)")
            elif after_mbps >= before_mbps * 0.95:  # Within 5% (acceptable)
                score += 25
                reasons.append(f"≈ Throughput stable ({tp_change:+.2f} Mbps, {tp_change_pct:+.1f}%)")
            elif after_mbps >= before_mbps * 0.90:  # 5-10% worse
                score -= 30
                reasons.append(f"⚠ Throughput decreased by {abs(tp_change):.2f} Mbps ({tp_change_pct:.1f}%)")
            else:  # >10% worse
                score -= 50
                reasons.append(f"✗ Throughput SIGNIFICANTLY DECREASED by {abs(tp_change):.2f} Mbps ({tp_change_pct:.1f}%)")
            
            metrics["throughput_before_mbps"] = before_mbps
            metrics["throughput_after_mbps"] = after_mbps
            metrics["throughput_change_mbps"] = tp_change
            metrics["throughput_change_percent"] = tp_change_pct
        else:
            reasons.append("⚠ Throughput test not available (iperf3 server required)")
            score += 25  # Neutral if not available
        
        # 2. Latency stability (20% weight)
        before_lat = before.get("tests", {}).get("latency", {})
        after_lat = after.get("tests", {}).get("latency", {})
        
        if before_lat.get("available") and after_lat.get("available"):
            before_avg = before_lat["avg_ms"]
            after_avg = after_lat["avg_ms"]
            
            if after_avg <= before_avg * 1.10:  # Latency didn't degrade much
                score += 20
                reasons.append(f"✓ Latency remained stable: {after_avg:.2f}ms")
            elif after_avg <= before_avg * 1.25:
                score += 10
                reasons.append(f"≈ Latency slightly increased: +{after_avg - before_avg:.2f}ms")
            else:
                score -= 20
                reasons.append(f"✗ Latency significantly increased: +{after_avg - before_avg:.2f}ms")
            
            metrics["latency_before_ms"] = before_avg
            metrics["latency_after_ms"] = after_avg
        
        # 3. Retransmits (20% weight) - if available
        if before_tp.get("available") and after_tp.get("available"):
            before_retrans = before_tp.get("retransmits", 0)
            after_retrans = after_tp.get("retransmits", 0)
            
            if after_retrans < before_retrans:
                score += 20
                reasons.append(f"✓ Retransmits reduced: {before_retrans} → {after_retrans}")
            elif after_retrans == before_retrans and after_retrans == 0:
                score += 20
                reasons.append(f"✓ No retransmits")
            elif after_retrans <= before_retrans * 1.5:
                score += 10
                reasons.append(f"≈ Retransmits acceptable: {after_retrans}")
            else:
                score -= 20
                reasons.append(f"✗ Retransmits increased: {before_retrans} → {after_retrans}")
            
            metrics["retransmits_before"] = before_retrans
            metrics["retransmits_after"] = after_retrans
        
        # Decision logic
        if score >= 60:
            decision = "KEEP"
            summary = f"Changes significantly improved throughput (score: {score}/100)"
        elif score >= 35:
            decision = "KEEP"
            summary = f"Changes improved performance (score: {score}/100)"
        elif score >= 15:
            decision = "UNCERTAIN"
            summary = f"Changes had mixed results (score: {score}/100)"
        else:
            decision = "ROLLBACK"
            summary = f"Changes degraded throughput (score: {score}/100) - rollback recommended"
        
        return {
            "decision": decision,
            "score": score,
            "summary": summary,
            "reasons": reasons,
            "metrics_comparison": metrics
        }
    
    @staticmethod
    def validate_streaming_profile(before: Dict, after: Dict) -> Dict:
        """
        Validate changes for streaming/video streaming workload.
        
        Streaming priorities (identical to throughput profile):
        1. Bandwidth increase (50% weight)
        2. Latency stability (20% weight)
        3. Retransmit reduction (20% weight)
        4. Connection stability (10% weight)
        
        This is an alias for validate_throughput_profile for consistency
        with profiles.yaml naming.
        """
        return ValidationEngine.validate_throughput_profile(before, after)
    
    @staticmethod
    def validate_video_calls_profile(before: Dict, after: Dict) -> Dict:
        """
        Validate changes for video conferencing workload.
        
        Video calls priorities:
        1. Latency (35% weight) - Important but not as critical as gaming
        2. Jitter (35% weight) - Critical for real-time media quality
        3. Packet loss (20% weight) - Affects call quality
        4. Connection stability (10% weight)
        
        Based on ITU-T G.114 standards for real-time communication.
        """
        score = 0
        reasons = []
        metrics = {}
        
        before_lat = before.get("tests", {}).get("latency", {})
        after_lat = after.get("tests", {}).get("latency", {})
        
        if not before_lat.get("available") or not after_lat.get("available"):
            return {
                "decision": "UNCERTAIN",
                "score": 0,
                "reasons": ["Latency tests not available for comparison"],
                "metrics_comparison": {}
            }
        
        # 1. Average Latency (35% weight) - Target: <150ms per ITU-T G.114
        before_avg = before_lat["avg_ms"]
        after_avg = after_lat["avg_ms"]
        latency_change = after_avg - before_avg
        latency_change_pct = (latency_change / before_avg) * 100
        
        if after_avg < 100:  # Excellent latency for video calls
            score += 35
            reasons.append(f"✓ EXCELLENT: Latency {after_avg:.2f}ms (<100ms target)")
        elif after_avg < 150:  # Good latency (ITU-T G.114 threshold)
            score += 25
            reasons.append(f"✓ GOOD: Latency {after_avg:.2f}ms (<150ms ITU-T threshold)")
        elif after_avg < before_avg:  # Improved but above threshold
            score += 15
            reasons.append(f"≈ Latency improved to {after_avg:.2f}ms (still above 150ms)")
        elif after_avg <= before_avg * 1.10:  # Within 10% (acceptable)
            score += 10
            reasons.append(f"≈ Latency stable at {after_avg:.2f}ms")
        else:  # Degraded
            score -= 20
            reasons.append(f"✗ Latency WORSENED by {abs(latency_change):.2f}ms")
        
        metrics["latency_before_ms"] = before_avg
        metrics["latency_after_ms"] = after_avg
        metrics["latency_change_ms"] = latency_change
        
        # 2. Jitter (35% weight) - Critical for video quality
        before_jitter = before_lat["jitter_ms"]
        after_jitter = after_lat["jitter_ms"]
        jitter_change = after_jitter - before_jitter
        
        if after_jitter < 20:  # Excellent jitter for video
            score += 35
            reasons.append(f"✓ EXCELLENT: Jitter {after_jitter:.2f}ms (<20ms target)")
        elif after_jitter < before_jitter * 0.90:  # Significant improvement
            score += 25
            reasons.append(f"✓ Jitter improved by {abs(jitter_change):.2f}ms")
        elif after_jitter <= before_jitter * 1.15:  # Within 15% (acceptable)
            score += 15
            reasons.append(f"≈ Jitter acceptable at {after_jitter:.2f}ms")
        else:  # Degraded
            score -= 20
            reasons.append(f"✗ Jitter increased by {abs(jitter_change):.2f}ms")
        
        metrics["jitter_before_ms"] = before_jitter
        metrics["jitter_after_ms"] = after_jitter
        
        # 3. Packet Loss (20% weight) - Affects call quality
        before_loss = before_lat.get("packet_loss_percent", 0)
        after_loss = after_lat.get("packet_loss_percent", 0)
        
        if after_loss < 0.1:  # Excellent loss rate
            score += 20
            reasons.append(f"✓ Excellent packet loss: {after_loss:.2f}%")
        elif after_loss < 1.0 and after_loss <= before_loss:
            score += 15
            reasons.append(f"✓ Good packet loss: {after_loss:.2f}%")
        elif after_loss <= before_loss * 1.5 and after_loss < 2.0:
            score += 5
            reasons.append(f"≈ Acceptable packet loss: {after_loss:.2f}%")
        else:
            score -= 20
            reasons.append(f"✗ High packet loss: {after_loss:.2f}%")
        
        metrics["packet_loss_before_pct"] = before_loss
        metrics["packet_loss_after_pct"] = after_loss
        
        # 4. Connection Time (10% weight)
        before_conn = before.get("tests", {}).get("connection_time", {})
        after_conn = after.get("tests", {}).get("connection_time", {})
        
        if before_conn.get("available") and after_conn.get("available"):
            before_conn_time = before_conn["avg_connect_ms"]
            after_conn_time = after_conn["avg_connect_ms"]
            
            if after_conn_time < before_conn_time * 0.9:
                score += 10
                reasons.append(f"✓ Connection time improved")
            elif after_conn_time <= before_conn_time * 1.15:
                score += 5
                reasons.append(f"≈ Connection time acceptable")
            else:
                score -= 5
                reasons.append(f"⚠ Connection time slower")
            
            metrics["connection_before_ms"] = before_conn_time
            metrics["connection_after_ms"] = after_conn_time
        
        # Decision logic
        if score >= 60:
            decision = "KEEP"
            summary = f"Changes improved video call performance (score: {score}/100)"
        elif score >= 35:
            decision = "KEEP"
            summary = f"Changes acceptable for video calls (score: {score}/100)"
        elif score >= 15:
            decision = "UNCERTAIN"
            summary = f"Changes had mixed results (score: {score}/100)"
        else:
            decision = "ROLLBACK"
            summary = f"Changes degraded video call quality (score: {score}/100)"
        
        return {
            "decision": decision,
            "score": score,
            "summary": summary,
            "reasons": reasons,
            "metrics_comparison": metrics
        }
    
    @staticmethod
    def validate_bulk_transfer_profile(before: Dict, after: Dict) -> Dict:
        """
        Validate changes for bulk file transfer workload.
        
        Bulk transfer priorities:
        1. Maximum throughput (70% weight) - Absolute priority
        2. Throughput stability (15% weight) - Consistency matters
        3. Retransmit reduction (15% weight) - Efficiency
        
        Latency and jitter are not considered for bulk transfers.
        """
        score = 0
        reasons = []
        metrics = {}
        
        before_tp = before.get("tests", {}).get("throughput", {})
        after_tp = after.get("tests", {}).get("throughput", {})
        
        if not (before_tp.get("available") and after_tp.get("available") and 
                "throughput_mbps" in before_tp and "throughput_mbps" in after_tp):
            return {
                "decision": "UNCERTAIN",
                "score": 0,
                "reasons": ["Throughput test not available (iperf3 server required for bulk transfer validation)"],
                "metrics_comparison": {}
            }
        
        # 1. Throughput (70% weight) - Maximum priority
        before_mbps = before_tp["throughput_mbps"]
        after_mbps = after_tp["throughput_mbps"]
        tp_change = after_mbps - before_mbps
        tp_change_pct = (tp_change / before_mbps) * 100 if before_mbps > 0 else 0
        
        if after_mbps > before_mbps * 1.15:  # 15%+ improvement
            score += 70
            reasons.append(f"✓ EXCELLENT: Throughput +{tp_change:.2f} Mbps ({tp_change_pct:.1f}% increase)")
        elif after_mbps > before_mbps * 1.05:  # 5-15% improvement
            score += 55
            reasons.append(f"✓ GOOD: Throughput +{tp_change:.2f} Mbps ({tp_change_pct:.1f}% increase)")
        elif after_mbps >= before_mbps * 0.98:  # Within 2% (acceptable)
            score += 40
            reasons.append(f"≈ Throughput stable ({tp_change:+.2f} Mbps)")
        elif after_mbps >= before_mbps * 0.95:  # 2-5% worse
            score -= 30
            reasons.append(f"⚠ Throughput decreased by {abs(tp_change):.2f} Mbps ({tp_change_pct:.1f}%)")
        else:  # >5% worse
            score -= 70
            reasons.append(f"✗ Throughput SIGNIFICANTLY DECREASED by {abs(tp_change):.2f} Mbps")
        
        metrics["throughput_before_mbps"] = before_mbps
        metrics["throughput_after_mbps"] = after_mbps
        metrics["throughput_change_mbps"] = tp_change
        
        # 2. Stability check (15% weight) - Standard deviation if available
        if "stddev_mbps" in before_tp and "stddev_mbps" in after_tp:
            # Lower stddev is better
            if after_tp["stddev_mbps"] < before_tp["stddev_mbps"]:
                score += 15
                reasons.append(f"✓ Throughput more stable")
            else:
                score += 5
                reasons.append(f"≈ Throughput stability acceptable")
        else:
            score += 10  # Neutral if not available
        
        # 3. Retransmits (15% weight)
        before_retrans = before_tp.get("retransmits", 0)
        after_retrans = after_tp.get("retransmits", 0)
        
        if after_retrans < before_retrans:
            score += 15
            reasons.append(f"✓ Retransmits reduced: {before_retrans} → {after_retrans}")
        elif after_retrans == before_retrans and after_retrans < 10:
            score += 10
            reasons.append(f"✓ Low retransmits: {after_retrans}")
        elif after_retrans <= before_retrans * 1.5:
            score += 5
            reasons.append(f"≈ Retransmits acceptable: {after_retrans}")
        else:
            score -= 15
            reasons.append(f"✗ Retransmits increased: {before_retrans} → {after_retrans}")
        
        metrics["retransmits_before"] = before_retrans
        metrics["retransmits_after"] = after_retrans
        
        # Decision logic - strict for bulk transfers
        if score >= 70:
            decision = "KEEP"
            summary = f"Changes significantly improved bulk transfer performance (score: {score}/100)"
        elif score >= 50:
            decision = "KEEP"
            summary = f"Changes improved bulk transfers (score: {score}/100)"
        elif score >= 30:
            decision = "UNCERTAIN"
            summary = f"Changes had minor impact (score: {score}/100)"
        else:
            decision = "ROLLBACK"
            summary = f"Changes degraded bulk transfer performance (score: {score}/100)"
        
        return {
            "decision": decision,
            "score": score,
            "summary": summary,
            "reasons": reasons,
            "metrics_comparison": metrics
        }
    
    @staticmethod
    def validate_server_profile(before: Dict, after: Dict) -> Dict:
        """
        Validate changes for server/high-concurrency workload.
        
        Server priorities (similar to balanced but with focus on stability):
        1. Latency stability (30% weight)
        2. Connection reliability (30% weight)
        3. Throughput (20% weight)
        4. DNS performance (20% weight)
        """
        score = 0
        reasons = []
        metrics = {}
        
        # 1. Latency stability (30% weight)
        before_lat = before.get("tests", {}).get("latency", {})
        after_lat = after.get("tests", {}).get("latency", {})
        
        if before_lat.get("available") and after_lat.get("available"):
            before_avg = before_lat["avg_ms"]
            after_avg = after_lat["avg_ms"]
            
            if after_avg < 50:  # Excellent server latency
                score += 30
                reasons.append(f"✓ EXCELLENT: Low latency {after_avg:.2f}ms")
            elif after_avg <= before_avg * 1.10:  # Within 10%
                score += 20
                reasons.append(f"✓ Latency stable at {after_avg:.2f}ms")
            elif after_avg <= before_avg * 1.25:
                score += 10
                reasons.append(f"≈ Latency acceptable at {after_avg:.2f}ms")
            else:
                score -= 20
                reasons.append(f"✗ Latency degraded to {after_avg:.2f}ms")
            
            metrics["latency_before_ms"] = before_avg
            metrics["latency_after_ms"] = after_avg
        
        # 2. Connection reliability (30% weight)
        before_conn = before.get("tests", {}).get("connection_time", {})
        after_conn = after.get("tests", {}).get("connection_time", {})
        before_loss = before_lat.get("packet_loss_percent", 0) if before_lat.get("available") else 0
        after_loss = after_lat.get("packet_loss_percent", 0) if after_lat.get("available") else 0
        
        conn_score = 0
        if before_conn.get("available") and after_conn.get("available"):
            after_conn_time = after_conn["avg_connect_ms"]
            if after_conn_time < 100:  # Fast connections
                conn_score += 15
                reasons.append(f"✓ Fast connections: {after_conn_time:.2f}ms")
            elif after_conn_time < 200:
                conn_score += 10
                reasons.append(f"✓ Good connection time: {after_conn_time:.2f}ms")
            else:
                conn_score += 5
            
            metrics["connection_after_ms"] = after_conn_time
        
        # Packet loss component
        if after_loss < 0.1:
            conn_score += 15
            reasons.append(f"✓ Excellent packet loss: {after_loss:.2f}%")
        elif after_loss < 1.0:
            conn_score += 10
            reasons.append(f"✓ Good packet loss: {after_loss:.2f}%")
        else:
            conn_score -= 10
            reasons.append(f"⚠ Packet loss: {after_loss:.2f}%")
        
        score += min(conn_score, 30)  # Cap at 30 points
        metrics["packet_loss_after_pct"] = after_loss
        
        # 3. Throughput (20% weight) - if available
        before_tp = before.get("tests", {}).get("throughput", {})
        after_tp = after.get("tests", {}).get("throughput", {})
        
        if (before_tp.get("available") and after_tp.get("available") and
            "throughput_mbps" in before_tp and "throughput_mbps" in after_tp):
            after_mbps = after_tp["throughput_mbps"]
            before_mbps = before_tp["throughput_mbps"]
            
            if after_mbps >= before_mbps * 0.95:  # Within 5%
                score += 20
                reasons.append(f"✓ Throughput stable: {after_mbps:.1f} Mbps")
            else:
                score += 10
                reasons.append(f"≈ Throughput: {after_mbps:.1f} Mbps")
            
            metrics["throughput_after_mbps"] = after_mbps
        else:
            score += 15  # Neutral if not available
        
        # 4. DNS performance (20% weight)
        before_dns = before.get("tests", {}).get("dns_resolution", {})
        after_dns = after.get("tests", {}).get("dns_resolution", {})
        
        if before_dns.get("available") and after_dns.get("available"):
            after_dns_ms = after_dns["avg_query_ms"]
            before_dns_ms = before_dns["avg_query_ms"]
            
            if after_dns_ms < 10:  # Excellent DNS
                score += 20
                reasons.append(f"✓ EXCELLENT: DNS {after_dns_ms:.2f}ms")
            elif after_dns_ms < 50:  # Good DNS
                score += 15
                reasons.append(f"✓ Good DNS performance: {after_dns_ms:.2f}ms")
            elif after_dns_ms <= before_dns_ms * 1.25:
                score += 10
                reasons.append(f"≈ DNS acceptable: {after_dns_ms:.2f}ms")
            else:
                score -= 10
                reasons.append(f"⚠ DNS slow: {after_dns_ms:.2f}ms")
            
            metrics["dns_after_ms"] = after_dns_ms
        else:
            score += 10  # Neutral
        
        # Decision logic
        if score >= 65:
            decision = "KEEP"
            summary = f"Changes improved server performance (score: {score}/100)"
        elif score >= 45:
            decision = "KEEP"
            summary = f"Changes acceptable for server workload (score: {score}/100)"
        elif score >= 25:
            decision = "UNCERTAIN"
            summary = f"Changes had mixed results (score: {score}/100)"
        else:
            decision = "ROLLBACK"
            summary = f"Changes degraded server performance (score: {score}/100)"
        
        return {
            "decision": decision,
            "score": score,
            "summary": summary,
            "reasons": reasons,
            "metrics_comparison": metrics
        }
    
    @staticmethod
    def validate_balanced_profile(before: Dict, after: Dict) -> Dict:
        """
        Validate changes for balanced workload.
        Equal weight to latency and throughput.
        """
        score = 0
        reasons = []
        metrics = {}
        
        # Run both gaming and throughput validations with adjusted weights
        gaming_result = ValidationEngine.validate_gaming_profile(before, after)
        throughput_result = ValidationEngine.validate_throughput_profile(before, after)
        
        # Average the scores
        gaming_score = gaming_result["score"]
        throughput_score = throughput_result["score"]
        score = (gaming_score + throughput_score) // 2
        
        # Combine reasons
        reasons.append(f"Gaming-focused score: {gaming_score}/100")
        reasons.append(f"Throughput-focused score: {throughput_score}/100")
        reasons.extend(gaming_result["reasons"][:2])  # Top 2 gaming reasons
        reasons.extend(throughput_result["reasons"][:2])  # Top 2 throughput reasons
        
        # Combine metrics
        metrics.update(gaming_result["metrics_comparison"])
        metrics.update(throughput_result["metrics_comparison"])
        
        # Decision logic
        if score >= 50:
            decision = "KEEP"
            summary = f"Changes improved overall performance (score: {score}/100)"
        elif score >= 20:
            decision = "UNCERTAIN"
            summary = f"Changes had mixed results (score: {score}/100)"
        else:
            decision = "ROLLBACK"
            summary = f"Changes degraded performance (score: {score}/100)"
        
        return {
            "decision": decision,
            "score": score,
            "summary": summary,
            "reasons": reasons,
            "metrics_comparison": metrics
        }
    
    @staticmethod
    def validate_low_latency_profile(before: Dict, after: Dict) -> Dict:
        """
        Validate changes for ultra-low-latency workload (HFT, real-time systems).
        Extremely strict on latency, tolerates lower throughput.
        """
        score = 0
        reasons = []
        metrics = {}
        
        before_lat = before.get("tests", {}).get("latency", {})
        after_lat = after.get("tests", {}).get("latency", {})
        
        if not before_lat.get("available") or not after_lat.get("available"):
            return {
                "decision": "UNCERTAIN",
                "score": 0,
                "reasons": ["Latency tests not available"],
                "metrics_comparison": {}
            }
        
        # Ultra-strict latency requirements
        before_avg = before_lat["avg_ms"]
        after_avg = after_lat["avg_ms"]
        before_max = before_lat["max_ms"]
        after_max = after_lat["max_ms"]
        
        # Average latency (50% weight)
        if after_avg < before_avg * 0.98:  
            score += 50
            reasons.append(f"✓ Average latency improved: {before_avg:.3f}ms → {after_avg:.3f}ms")
        elif after_avg <= before_avg * 1.01:  # Within 1% is acceptable
            score += 30
            reasons.append(f"≈ Average latency stable: {after_avg:.3f}ms")
        else:  # Any increase is bad
            score -= 50
            reasons.append(f"✗ Average latency INCREASED: {before_avg:.3f}ms → {after_avg:.3f}ms")
        
        # Max latency / tail latency (50% weight)
        if after_max < before_max * 0.95:
            score += 50
            reasons.append(f"✓ Max latency improved: {before_max:.3f}ms → {after_max:.3f}ms")
        elif after_max <= before_max * 1.05:
            score += 30
            reasons.append(f"≈ Max latency acceptable: {after_max:.3f}ms")
        else:
            score -= 50
            reasons.append(f"✗ Max latency WORSENED: {before_max:.3f}ms → {after_max:.3f}ms")
        
        metrics["latency_avg_before_ms"] = before_avg
        metrics["latency_avg_after_ms"] = after_avg
        metrics["latency_max_before_ms"] = before_max
        metrics["latency_max_after_ms"] = after_max
        
        # Decision: Very strict
        if score >= 60:
            decision = "KEEP"
            summary = f"Changes met low-latency requirements (score: {score}/100)"
        elif score >= 20:
            decision = "UNCERTAIN"
            summary = f"Changes borderline for low-latency (score: {score}/100)"
        else:
            decision = "ROLLBACK"
            summary = f"Changes FAILED low-latency requirements (score: {score}/100)"
        
        return {
            "decision": decision,
            "score": score,
            "summary": summary,
            "reasons": reasons,
            "metrics_comparison": metrics
        }
    
    @staticmethod
    def compare_benchmarks(before: Dict, after: Dict, profile: str = "gaming") -> Dict:
        """
        Main entry point for validation.
        Compares before/after benchmarks based on specified profile.
        
        Supports profiles from profiles.yaml:
        - gaming: Ultra-low latency for competitive gaming
        - streaming: High throughput for video streaming
        - video_calls: Balanced for video conferencing (ITU-T G.114)
        - bulk_transfer: Maximum throughput for file transfers
        - server: High-concurrency server workloads
        
        Args:
            before: Benchmark results before changes
            after: Benchmark results after changes
            profile: Validation profile name
        
        Returns:
            Validation result with decision, score, and detailed comparison
        """
        # Normalize profile name (handle aliases and case variations)
        normalized_profile = OPTIMIZATION_PROFILES.get(profile.lower(), profile.lower())
        
        # Map profiles to validator functions
        validators = {
            "gaming": ValidationEngine.validate_gaming_profile,
            "streaming": ValidationEngine.validate_streaming_profile,
            "video_calls": ValidationEngine.validate_video_calls_profile,
            "bulk_transfer": ValidationEngine.validate_bulk_transfer_profile,
            "server": ValidationEngine.validate_server_profile,
            "balanced": ValidationEngine.validate_balanced_profile,
            
            # Legacy: throughput is now streaming
            "throughput": ValidationEngine.validate_throughput_profile,
        }
        
        validator = validators.get(normalized_profile, ValidationEngine.validate_gaming_profile)
        result = validator(before, after)
        
        result["profile"] = profile
        result["before_timestamp"] = before.get("timestamp", "unknown")
        result["after_timestamp"] = after.get("timestamp", "unknown")
        
        # Log the validation test
        log_validation_test(
            profile,
            before,
            after,
            result["decision"],
            result["score"]
        )
        
        return result
