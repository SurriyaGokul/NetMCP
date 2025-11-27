import matplotlib.pyplot as plt
import numpy as np

video_calls_data = {
    'profile': 'Video Calls',
    'before': {
        'latency_avg': 20.545,
        'jitter': 57.60,
        'packet_loss': 0.0,
        'connection_time': 44.323,
        'dns_time': 19.0
    },
    'after': {
        'latency_avg': 19.295,
        'jitter': 45.80,
        'packet_loss': 0.0,
        'connection_time': 39.944,
        'dns_time': 14.8
    }
}

bulk_transfer_data = {
    'profile': 'Bulk Transfer',
    'before': {
        'latency_avg': 29.42,
        'jitter': 106.00,
        'packet_loss': 0.0,
        'connection_time': 45.63,
        'dns_time': 16.60
    },
    'after': {
        'latency_avg': 18.44,
        'jitter': 13.00,
        'packet_loss': 0.0,
        'connection_time': 38.28,
        'dns_time': 15.40
    }
}

streaming_data = {
    'profile': 'Streaming',
    'before': {
        'latency_avg': 18.48,
        'jitter': 11.70,
        'connection_time': 49.31,
        'dns_time': 17.00
    },
    'after': {
        'latency_avg': 18.16,
        'jitter': 15.10,
        'connection_time': 38.89,
        'dns_time': 14.20
    }
}

server_data = {
    'profile': 'Server',
    'before': {
        'latency_avg': 19.21,
        'jitter': 25.20,
        'max_latency': 40.6,
        'dns_time': 19.80,
        'connection_time': 24.99,
        'packet_loss': 0.0
    },
    'after': {
        'latency_avg': 17.25,
        'jitter': 18.00,
        'max_latency': 33.1,
        'dns_time': 13.40,
        'connection_time': 25.62,
        'packet_loss': 0.0
    }
}

def create_bulk_transfer_plot():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Performance metrics
    metrics = ['Latency Avg\n(ms)', 'Jitter\n(ms)', 'Connection\nTime (ms)', 'DNS Query\n(ms)']
    before_vals = [bulk_transfer_data['before']['latency_avg'],
                   bulk_transfer_data['before']['jitter'],
                   bulk_transfer_data['before']['connection_time'],
                   bulk_transfer_data['before']['dns_time']]
    after_vals = [bulk_transfer_data['after']['latency_avg'],
                  bulk_transfer_data['after']['jitter'],
                  bulk_transfer_data['after']['connection_time'],
                  bulk_transfer_data['after']['dns_time']]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    bars1 = ax1.bar(x - width/2, before_vals, width, label='Balanced (Before)', color='#ff6b6b', alpha=0.8)
    bars2 = ax1.bar(x + width/2, after_vals, width, label='Bulk Transfer', color='#51cf66', alpha=0.8)
    
    ax1.set_ylabel('Time (ms)', fontsize=11, fontweight='bold')
    ax1.set_title('Bulk Transfer Profile: Performance Metrics', fontsize=13, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(metrics, fontsize=9)
    ax1.legend(fontsize=10)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}',
                    ha='center', va='bottom', fontsize=8)
    
    # Improvements
    latency_imp = ((bulk_transfer_data['before']['latency_avg'] - bulk_transfer_data['after']['latency_avg']) / 
                   bulk_transfer_data['before']['latency_avg'] * 100)
    jitter_imp = ((bulk_transfer_data['before']['jitter'] - bulk_transfer_data['after']['jitter']) / 
                  bulk_transfer_data['before']['jitter'] * 100)
    conn_imp = ((bulk_transfer_data['before']['connection_time'] - bulk_transfer_data['after']['connection_time']) / 
                bulk_transfer_data['before']['connection_time'] * 100)
    dns_imp = ((bulk_transfer_data['before']['dns_time'] - bulk_transfer_data['after']['dns_time']) / 
               bulk_transfer_data['before']['dns_time'] * 100)
    
    improvement_labels = ['Latency\nReduction', 'Jitter\nReduction', 'Connection\nTime', 'DNS\nQuery Time']
    improvements = [latency_imp, jitter_imp, conn_imp, dns_imp]
    
    bars = ax2.bar(improvement_labels, improvements, color='#339af0', alpha=0.8)
    ax2.set_ylabel('Improvement (%)', fontsize=11, fontweight='bold')
    ax2.set_title('Bulk Transfer Profile: Performance Improvements', fontsize=13, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3, linestyle='--')
    
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%',
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('results/bulk_transfer_profile_comparison.png', dpi=300, bbox_inches='tight')
    print("✓ Bulk Transfer profile plot saved")

def create_streaming_plot():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Performance metrics
    metrics = ['Latency\n(ms)', 'Jitter\n(ms)', 'Connection\nTime (ms)', 'DNS Query\n(ms)']
    before_vals = [streaming_data['before']['latency_avg'],
                   streaming_data['before']['jitter'],
                   streaming_data['before']['connection_time'],
                   streaming_data['before']['dns_time']]
    after_vals = [streaming_data['after']['latency_avg'],
                  streaming_data['after']['jitter'],
                  streaming_data['after']['connection_time'],
                  streaming_data['after']['dns_time']]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    bars1 = ax1.bar(x - width/2, before_vals, width, label='Balanced (Before)', color='#ff6b6b', alpha=0.8)
    bars2 = ax1.bar(x + width/2, after_vals, width, label='Streaming', color='#51cf66', alpha=0.8)
    
    ax1.set_ylabel('Time (ms)', fontsize=11, fontweight='bold')
    ax1.set_title('Streaming Profile: Performance Metrics', fontsize=13, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(metrics, fontsize=9)
    ax1.legend(fontsize=10)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}',
                    ha='center', va='bottom', fontsize=8)
    
    # Improvements (note: jitter increased, so it's negative improvement)
    latency_imp = ((streaming_data['before']['latency_avg'] - streaming_data['after']['latency_avg']) / 
                   streaming_data['before']['latency_avg'] * 100)
    jitter_change = ((streaming_data['after']['jitter'] - streaming_data['before']['jitter']) / 
                     streaming_data['before']['jitter'] * 100)  # This will be negative (worse)
    conn_imp = ((streaming_data['before']['connection_time'] - streaming_data['after']['connection_time']) / 
                streaming_data['before']['connection_time'] * 100)
    dns_imp = ((streaming_data['before']['dns_time'] - streaming_data['after']['dns_time']) / 
               streaming_data['before']['dns_time'] * 100)
    
    improvement_labels = ['Latency\nReduction', 'Jitter\nChange', 'Connection\nTime', 'DNS\nQuery Time']
    improvements = [latency_imp, -jitter_change, conn_imp, dns_imp]  # Negate jitter to show as negative
    colors = ['#339af0', '#ff6b6b', '#339af0', '#339af0']  # Red for jitter (degraded)
    
    bars = ax2.bar(improvement_labels, improvements, color=colors, alpha=0.8)
    ax2.set_ylabel('Change (%)', fontsize=11, fontweight='bold')
    ax2.set_title('Streaming Profile: Performance Changes', fontsize=13, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3, linestyle='--')
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%',
                ha='center', va='bottom' if height > 0 else 'top', fontsize=9, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('results/streaming_profile_comparison.png', dpi=300, bbox_inches='tight')
    print("✓ Streaming profile plot saved")

import matplotlib.pyplot as plt
import numpy as np

plt.style.use('seaborn-v0_8-darkgrid')
colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E']

def create_gaming_plot():
    metrics = ['Avg Latency\n(ms)', 'Jitter\n(ms)', 'Max Latency\n(ms)', 
               'Connection\nTime (ms)', 'DNS Query\n(ms)', 'Multi-Host\nAvg (ms)']
    before = [18.90, 46.20, 61.1, 29.32, 18.40, 12.05]
    after = [19.97, 32.40, 47.3, 24.30, 24.00, 10.72]
    
    # Calculate percentage changes
    pct_changes = [((after[i] - before[i]) / before[i]) * 100 for i in range(len(before))]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Left plot: Absolute values
    x = np.arange(len(metrics))
    width = 0.35
    
    bars1 = ax1.bar(x - width/2, before, width, label='Before (Balanced)', 
                    color=colors[0], alpha=0.8, edgecolor='black', linewidth=1.2)
    bars2 = ax1.bar(x + width/2, after, width, label='After (Gaming)', 
                    color=colors[1], alpha=0.8, edgecolor='black', linewidth=1.2)
    
    ax1.set_ylabel('Value', fontsize=12, fontweight='bold')
    ax1.set_title('Gaming Profile: Before vs After', fontsize=14, fontweight='bold', pad=20)
    ax1.set_xticks(x)
    ax1.set_xticklabels(metrics, fontsize=10)
    ax1.legend(fontsize=10, framealpha=0.9)
    ax1.grid(axis='y', alpha=0.3)
    
    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # Right plot: Percentage changes
    colors_pct = [colors[3] if x > 0 else colors[4] for x in pct_changes]
    bars3 = ax2.barh(metrics, pct_changes, color=colors_pct, alpha=0.8, 
                     edgecolor='black', linewidth=1.2)
    
    ax2.set_xlabel('Percentage Change (%)', fontsize=12, fontweight='bold')
    ax2.set_title('Gaming Profile: Performance Changes', fontsize=14, fontweight='bold', pad=20)
    ax2.axvline(x=0, color='black', linestyle='-', linewidth=1.5)
    ax2.grid(axis='x', alpha=0.3)
    
    # Add percentage labels
    for i, (bar, pct) in enumerate(zip(bars3, pct_changes)):
        width = bar.get_width()
        label_x = width + (2 if width > 0 else -2)
        ax2.text(label_x, bar.get_y() + bar.get_height()/2.,
                f'{pct:+.1f}%',
                ha='left' if width > 0 else 'right',
                va='center', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('results/gaming_profile_comparison.png', dpi=300, bbox_inches='tight')
    print("✓ Gaming profile plot saved: results/gaming_profile_comparison.png")
    plt.close()

def create_video_calls_plot():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Metrics comparison
    metrics = ['Latency Avg\n(ms)', 'Jitter\n(ms)', 'Connection\nTime (ms)', 'DNS Query\n(ms)']
    before_vals = [video_calls_data['before']['latency_avg'],
                   video_calls_data['before']['jitter'],
                   video_calls_data['before']['connection_time'],
                   video_calls_data['before']['dns_time']]
    after_vals = [video_calls_data['after']['latency_avg'],
                  video_calls_data['after']['jitter'],
                  video_calls_data['after']['connection_time'],
                  video_calls_data['after']['dns_time']]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    bars1 = ax1.bar(x - width/2, before_vals, width, label='Balanced (Before)', color='#ff6b6b', alpha=0.8)
    bars2 = ax1.bar(x + width/2, after_vals, width, label='Video Calls', color='#51cf66', alpha=0.8)
    
    ax1.set_ylabel('Time (ms)', fontsize=11, fontweight='bold')
    ax1.set_title('Video Calls Profile: Performance Metrics', fontsize=13, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(metrics, fontsize=9)
    ax1.legend(fontsize=10)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}',
                    ha='center', va='bottom', fontsize=8)
    
    # Improvements
    latency_imp = ((video_calls_data['before']['latency_avg'] - video_calls_data['after']['latency_avg']) / 
                   video_calls_data['before']['latency_avg'] * 100)
    jitter_imp = ((video_calls_data['before']['jitter'] - video_calls_data['after']['jitter']) / 
                  video_calls_data['before']['jitter'] * 100)
    conn_imp = ((video_calls_data['before']['connection_time'] - video_calls_data['after']['connection_time']) / 
                video_calls_data['before']['connection_time'] * 100)
    dns_imp = ((video_calls_data['before']['dns_time'] - video_calls_data['after']['dns_time']) / 
               video_calls_data['before']['dns_time'] * 100)
    
    improvement_labels = ['Latency\nReduction', 'Jitter\nReduction', 'Connection\nTime', 'DNS\nQuery Time']
    improvements = [latency_imp, jitter_imp, conn_imp, dns_imp]
    
    bars = ax2.bar(improvement_labels, improvements, color='#339af0', alpha=0.8)
    ax2.set_ylabel('Improvement (%)', fontsize=11, fontweight='bold')
    ax2.set_title('Video Calls Profile: Performance Improvements', fontsize=13, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3, linestyle='--')
    
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%',
                ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('results/video_calls_profile_comparison.png', dpi=300, bbox_inches='tight')
    print("✓ Video Calls profile plot saved")

def create_server_plot():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Metrics comparison
    metrics = ['Latency Avg\n(ms)', 'Jitter\n(ms)', 'Max Latency\n(ms)', 'DNS Query\n(ms)', 'Connection\nTime (ms)']
    before_vals = [server_data['before']['latency_avg'],
                   server_data['before']['jitter'],
                   server_data['before']['max_latency'],
                   server_data['before']['dns_time'],
                   server_data['before']['connection_time']]
    after_vals = [server_data['after']['latency_avg'],
                  server_data['after']['jitter'],
                  server_data['after']['max_latency'],
                  server_data['after']['dns_time'],
                  server_data['after']['connection_time']]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    bars1 = ax1.bar(x - width/2, before_vals, width, label='Balanced (Before)', color='#ff6b6b', alpha=0.8)
    bars2 = ax1.bar(x + width/2, after_vals, width, label='Server', color='#51cf66', alpha=0.8)
    
    ax1.set_ylabel('Time (ms)', fontsize=11, fontweight='bold')
    ax1.set_title('Server Profile: Performance Metrics', fontsize=13, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(metrics, fontsize=8)
    ax1.legend(fontsize=10)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}',
                    ha='center', va='bottom', fontsize=7)
    
    # Improvements
    latency_imp = ((server_data['before']['latency_avg'] - server_data['after']['latency_avg']) / 
                   server_data['before']['latency_avg'] * 100)
    jitter_imp = ((server_data['before']['jitter'] - server_data['after']['jitter']) / 
                  server_data['before']['jitter'] * 100)
    max_lat_imp = ((server_data['before']['max_latency'] - server_data['after']['max_latency']) / 
                   server_data['before']['max_latency'] * 100)
    dns_imp = ((server_data['before']['dns_time'] - server_data['after']['dns_time']) / 
               server_data['before']['dns_time'] * 100)
    
    improvement_labels = ['Latency\nReduction', 'Jitter\nReduction', 'Max Latency\nReduction', 'DNS\nQuery Time']
    improvements = [latency_imp, jitter_imp, max_lat_imp, dns_imp]
    
    bars = ax2.bar(improvement_labels, improvements, color='#339af0', alpha=0.8)
    ax2.set_ylabel('Improvement (%)', fontsize=11, fontweight='bold')
    ax2.set_title('Server Profile: Performance Improvements', fontsize=13, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3, linestyle='--')
    
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%',
                ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('results/server_profile_comparison.png', dpi=300, bbox_inches='tight')
    print("✓ Server profile plot saved")

if __name__ == "__main__":
    print("=" * 70)
    print("GENERATING COMPARISON PLOTS FOR ALL FIVE PROFILES")
    print("Based on ACTUAL test results from network performance benchmarks")
    print("Baseline: Balanced profile (default system state)")
    print("=" * 70)
    print()
    create_gaming_plot()
    create_video_calls_plot()
    create_bulk_transfer_plot()
    create_streaming_plot()
    create_server_plot()
    print()
    print("=" * 70)
    print("All plots generated successfully!")
    print("=" * 70)
    print("\nFiles saved in results/ directory:")
    print("  1. gaming_profile_comparison.png")
    print("  2. video_calls_profile_comparison.png")
    print("  3. bulk_transfer_profile_comparison.png")
    print("  4. streaming_profile_comparison.png")
    print("  5. server_profile_comparison.png")
    print()
