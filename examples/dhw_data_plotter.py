#!/usr/bin/env python3
"""
DHW Charge Data Plotter and Analyzer

Reads data from dhw_charge_logger.py and creates visualizations:
- DHW charge percentage over time
- Temperature trends
- Operation mode analysis  
- Power consumption patterns
- Heat pump vs electric heating efficiency

Requires: matplotlib, pandas, seaborn
Install with: pip install matplotlib pandas seaborn
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from datetime import datetime
from pathlib import Path
import sys

# Set style for better looking plots
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

def load_dhw_data(json_file: str = "dhw_charge_data.json") -> pd.DataFrame:
    """Load DHW data from JSON file."""
    file_path = Path(json_file)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Data file not found: {json_file}")
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    if not data:
        raise ValueError("No data found in file")
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Convert timestamp to datetime
    df['datetime'] = pd.to_datetime(df['iso_timestamp'])
    df = df.set_index('datetime')
    
    print(f"📊 Loaded {len(df)} data points from {json_file}")
    print(f"📅 Date range: {df.index.min()} to {df.index.max()}")
    
    return df

def plot_dhw_charge_overview(df: pd.DataFrame, save_path: str = "dhw_charge_overview.png"):
    """Create comprehensive DHW charge analysis plot."""
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Navien NWP500 - DHW Charge Analysis', fontsize=16, fontweight='bold')
    
    # 1. DHW Charge Percentage Over Time
    ax1 = axes[0, 0]
    ax1.plot(df.index, df['dhw_charge_percentage'], linewidth=2, color='blue', alpha=0.8)
    ax1.fill_between(df.index, df['dhw_charge_percentage'], alpha=0.3, color='blue')
    ax1.set_title('DHW Tank Charge Level', fontweight='bold')
    ax1.set_ylabel('Charge Percentage (%)')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(0, 100)
    
    # Add horizontal lines for reference
    ax1.axhline(y=75, color='green', linestyle='--', alpha=0.5, label='Good (75%)')
    ax1.axhline(y=50, color='orange', linestyle='--', alpha=0.5, label='Medium (50%)')
    ax1.axhline(y=25, color='red', linestyle='--', alpha=0.5, label='Low (25%)')
    ax1.legend()
    
    # 2. Temperature Trends
    ax2 = axes[0, 1]
    ax2.plot(df.index, df['dhw_temperature'], label='Actual Temp', linewidth=2)
    ax2.plot(df.index, df['dhw_temperature_setting'], label='Target Temp', linewidth=2, linestyle='--')
    ax2.plot(df.index, df['outside_temperature'], label='Outside Temp', linewidth=1, alpha=0.7)
    ax2.set_title('Temperature Trends', fontweight='bold')
    ax2.set_ylabel('Temperature (°F)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. Operation Mode Analysis
    ax3 = axes[1, 0]
    
    # Create operation mode timeline
    mode_colors = {
        'heat_pump_only': 'green',
        'electric_only': 'red', 
        'hybrid': 'orange',
        'standby': 'gray',
        'heating_unknown': 'purple'
    }
    
    for mode, color in mode_colors.items():
        mode_data = df[df['hp_operation_mode'] == mode]
        if not mode_data.empty:
            ax3.scatter(mode_data.index, [mode] * len(mode_data), 
                       c=color, label=mode.replace('_', ' ').title(), 
                       alpha=0.7, s=20)
    
    ax3.set_title('Heat Pump Operation Modes', fontweight='bold')
    ax3.set_ylabel('Operation Mode')
    ax3.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax3.grid(True, alpha=0.3)
    
    # 4. Power Consumption
    ax4 = axes[1, 1]
    ax4.plot(df.index, df['current_inst_power'], linewidth=2, color='purple')
    ax4.fill_between(df.index, df['current_inst_power'], alpha=0.3, color='purple')
    ax4.set_title('Instantaneous Power Consumption', fontweight='bold')
    ax4.set_ylabel('Power (Watts)')
    ax4.grid(True, alpha=0.3)
    
    # Format x-axis for all subplots
    for ax in axes.flat:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M\n%m/%d'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=4))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha='center')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.show()
    
    print(f"📈 Plot saved as: {save_path}")

def analyze_efficiency_patterns(df: pd.DataFrame):
    """Analyze heat pump efficiency patterns."""
    
    print("\n🔍 DHW CHARGE EFFICIENCY ANALYSIS")
    print("=" * 50)
    
    # Basic statistics
    print(f"📊 Average DHW Charge: {df['dhw_charge_percentage'].mean():.1f}%")
    print(f"📈 Max DHW Charge: {df['dhw_charge_percentage'].max():.1f}%")
    print(f"📉 Min DHW Charge: {df['dhw_charge_percentage'].min():.1f}%")
    print(f"📏 Charge Range: {df['dhw_charge_percentage'].max() - df['dhw_charge_percentage'].min():.1f}%")
    
    # Operation mode distribution
    print(f"\n🔧 OPERATION MODE DISTRIBUTION")
    mode_counts = df['hp_operation_mode'].value_counts()
    total_points = len(df)
    
    for mode, count in mode_counts.items():
        percentage = (count / total_points) * 100
        print(f"   {mode.replace('_', ' ').title()}: {count} points ({percentage:.1f}%)")
    
    # Power consumption analysis
    print(f"\n⚡ POWER CONSUMPTION ANALYSIS")
    print(f"   Average Power: {df['current_inst_power'].mean():.1f}W")
    print(f"   Max Power: {df['current_inst_power'].max():.1f}W")
    print(f"   Min Power: {df['current_inst_power'].min():.1f}W")
    
    # Heat pump vs electric efficiency (when data available)
    hp_data = df[df['hp_operation_mode'] == 'heat_pump_only']
    electric_data = df[df['hp_operation_mode'] == 'electric_only']
    
    if not hp_data.empty and not electric_data.empty:
        print(f"\n🏭 HEATING MODE EFFICIENCY")
        print(f"   Heat Pump Only - Avg Power: {hp_data['current_inst_power'].mean():.1f}W")
        print(f"   Electric Only - Avg Power: {electric_data['current_inst_power'].mean():.1f}W")
        
        if hp_data['current_inst_power'].mean() > 0 and electric_data['current_inst_power'].mean() > 0:
            efficiency_ratio = electric_data['current_inst_power'].mean() / hp_data['current_inst_power'].mean()
            print(f"   Electric/Heat Pump Power Ratio: {efficiency_ratio:.2f}x")
    
    # DHW usage patterns
    dhw_use_active = df[df['dhw_use'] > 0]
    if not dhw_use_active.empty:
        print(f"\n🚿 DHW USAGE PATTERNS")
        print(f"   Active DHW Use: {len(dhw_use_active)} points ({len(dhw_use_active)/len(df)*100:.1f}%)")
        print(f"   Avg Charge During Use: {dhw_use_active['dhw_charge_percentage'].mean():.1f}%")
        print(f"   Avg Charge When Idle: {df[df['dhw_use'] == 0]['dhw_charge_percentage'].mean():.1f}%")

def plot_detailed_analysis(df: pd.DataFrame, save_path: str = "dhw_detailed_analysis.png"):
    """Create detailed analysis plots."""
    
    fig, axes = plt.subplots(3, 1, figsize=(16, 12))
    fig.suptitle('Navien NWP500 - Detailed Performance Analysis', fontsize=16, fontweight='bold')
    
    # 1. DHW Charge vs Power Consumption
    ax1 = axes[0]
    
    # Color by operation mode
    mode_colors = {'heat_pump_only': 'green', 'electric_only': 'red', 'hybrid': 'orange', 
                   'standby': 'gray', 'heating_unknown': 'purple'}
    
    for mode, color in mode_colors.items():
        mode_data = df[df['hp_operation_mode'] == mode]
        if not mode_data.empty:
            ax1.scatter(mode_data['dhw_charge_percentage'], mode_data['current_inst_power'], 
                       c=color, label=mode.replace('_', ' ').title(), alpha=0.6, s=30)
    
    ax1.set_xlabel('DHW Charge Percentage (%)')
    ax1.set_ylabel('Power Consumption (W)')
    ax1.set_title('DHW Charge vs Power Consumption (by Operation Mode)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. Temperature Delta Analysis
    ax2 = axes[1]
    df['temp_delta'] = df['dhw_temperature'] - df['dhw_temperature_setting']
    ax2.plot(df.index, df['temp_delta'], linewidth=2, color='red')
    ax2.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    ax2.fill_between(df.index, df['temp_delta'], alpha=0.3, color='red')
    ax2.set_ylabel('Temperature Delta (°F)')
    ax2.set_title('Actual vs Target Temperature Difference')
    ax2.grid(True, alpha=0.3)
    
    # 3. System Status Timeline
    ax3 = axes[2]
    
    # Stack different status indicators
    ax3.fill_between(df.index, 0, df['operation_busy'], label='Operation Busy', alpha=0.7)
    ax3.fill_between(df.index, 0, df['current_heat_use'], label='Heating Active', alpha=0.7)
    ax3.fill_between(df.index, 0, df['dhw_use'], label='DHW Use', alpha=0.7)
    
    ax3.set_ylabel('System Status')
    ax3.set_title('System Activity Timeline')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Format x-axis
    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M\n%m/%d'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=4))
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.show()
    
    print(f"📈 Detailed plot saved as: {save_path}")

def main():
    """Main plotter function."""
    
    # Check for data file
    json_file = "dhw_charge_data.json"
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    
    try:
        # Load data
        df = load_dhw_data(json_file)
        
        # Create plots
        plot_dhw_charge_overview(df)
        plot_detailed_analysis(df)
        
        # Print analysis
        analyze_efficiency_patterns(df)
        
        print(f"\n✅ Analysis complete! Check the generated PNG files.")
        
    except FileNotFoundError:
        print(f"❌ Data file not found: {json_file}")
        print("💡 Run dhw_charge_logger.py first to collect data")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()