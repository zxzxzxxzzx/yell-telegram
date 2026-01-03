import io
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from typing import List, Tuple

plt.switch_backend('Agg')

def generate_stats_chart(
    daily_stats: List[Tuple[str, int, int]],
    period_label: str = "Last 30 days"
) -> io.BytesIO:
    if not daily_stats:
        dates = []
        messages = []
    else:
        dates = [datetime.strptime(row[0], '%Y-%m-%d') for row in daily_stats]
        messages = [row[1] for row in daily_stats]
    
    fig, ax = plt.subplots(figsize=(10, 5))
    
    if dates:
        ax.plot(dates, messages, color='#e53935', linewidth=2, marker='o', markersize=6)
        
        ax.set_ylabel('Messages', fontsize=11)
        ax.set_xlabel('Date', fontsize=11)
        
        if len(dates) == 1:
            single_date = dates[0]
            ax.set_xlim(single_date - timedelta(days=1), single_date + timedelta(days=1))
            ax.set_xticks([single_date])
            ax.set_xticklabels([single_date.strftime('%d %b %Y')])
        else:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
            if len(dates) <= 7:
                ax.xaxis.set_major_locator(mdates.DayLocator())
            else:
                ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=10))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        max_msg = max(messages) if messages else 1
        ax.set_ylim(bottom=0, top=max_msg * 1.2 if max_msg > 0 else 1)
        ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
        ax.grid(True, alpha=0.3)
    else:
        ax.text(0.5, 0.5, 'No data available', fontsize=14, color='grey',
                ha='center', va='center', transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])
    
    ax.set_title(f'Message Trend ({period_label})', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=120, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    
    return buf
