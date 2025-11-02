"""
Validation engine for comparing network performance before and after configuration changes.
Makes intelligent decisions about whether changes improved or worsened performance.
"""

from typing import Dict, List, Optional
import json


class ValidationEngine:
    """
    Compares before/after performance metrics and decides if changes are beneficial.
    """
    
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
        latency_change_pct = (latency_change / before_avg) * 100
        
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
        if after_avg < before_avg * 0.98:  # Even 2% improvement is good
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
        
        Args:
            before: Benchmark results before changes
            after: Benchmark results after changes
            profile: Validation profile (gaming, throughput, balanced, low-latency)
        
        Returns:
            Validation result with decision, score, and detailed comparison
        """
        validators = {
            "gaming": ValidationEngine.validate_gaming_profile,
            "throughput": ValidationEngine.validate_throughput_profile,
            "balanced": ValidationEngine.validate_balanced_profile,
            "low-latency": ValidationEngine.validate_low_latency_profile,
            "low_latency": ValidationEngine.validate_low_latency_profile,
        }
        
        validator = validators.get(profile.lower(), ValidationEngine.validate_balanced_profile)
        result = validator(before, after)
        
        result["profile"] = profile
        result["before_timestamp"] = before.get("timestamp", "unknown")
        result["after_timestamp"] = after.get("timestamp", "unknown")
        
        return result
