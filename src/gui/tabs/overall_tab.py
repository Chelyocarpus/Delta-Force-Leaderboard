from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QGridLayout, 
                           QLabel, QToolTip)
from PyQt5.QtCore import Qt, QMargins, QSettings  # Added QSettings import
from PyQt5.QtChart import (QChart, QChartView, QBarSet, QBarSeries,
                          QBarCategoryAxis, QValueAxis, QChart, QLegend)
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QFont, QFont, QCursor
from ..widgets.numeric_sort import NumericSortItem
from ...utils.constants import (HISTORY_TABLE_COLUMNS, QUERY_PLAYER_STATS,
                              QUERY_FAVORITE_CLASS, QUERY_VICTORY_STATS,
                              PLAYER_CLASSES)
import sqlite3
import logging

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

QUERY_FAVORITE_CLASS = """
    SELECT class
    FROM matches
    WHERE player_name = ?
    GROUP BY class
    ORDER BY COUNT(*) DESC
    LIMIT 1
"""

class ResizableChartView(QChartView):
    def __init__(self, chart, settings):
        super().__init__(chart)
        self.settings = settings

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Save height when resized
        self.settings.setValue('chartGroupHeight', self.height())

def create_monthly_performance_chart(cursor, player_name):
    logger.info(f"Creating chart for player: {player_name}")
    try:
        cursor.execute("""
            WITH month_data AS (
                SELECT 
                    substr(match_date, 4, 9) as month_year,  -- Extract "MMM YYYY" part
                    kills, deaths, assists, revives
                FROM matches 
                WHERE player_name = ?
            )
            SELECT 
                month_year,
                ROUND(AVG(CAST(kills AS FLOAT)), 1) as avg_kills,
                ROUND(AVG(CAST(deaths AS FLOAT)), 1) as avg_deaths,
                ROUND(AVG(CAST(assists AS FLOAT)), 1) as avg_assists,
                ROUND(AVG(CAST(revives AS FLOAT)), 1) as avg_revives,
                COUNT(*) as games_played,
                GROUP_CONCAT(month_year) as dates_included
            FROM month_data
            GROUP BY month_year
            ORDER BY substr(month_year, -4) DESC, -- Year
                     CASE substr(month_year, 1, 3) -- Month
                        WHEN 'Jan' THEN '01'
                        WHEN 'Feb' THEN '02'
                        WHEN 'Mar' THEN '03'
                        WHEN 'Apr' THEN '04'
                        WHEN 'May' THEN '05'
                        WHEN 'Jun' THEN '06'
                        WHEN 'Jul' THEN '07'
                        WHEN 'Aug' THEN '08'
                        WHEN 'Sep' THEN '09'
                        WHEN 'Oct' THEN '10'
                        WHEN 'Nov' THEN '11'
                        WHEN 'Dec' THEN '12'
                     END DESC
            LIMIT 3
        """, (player_name,))

        data = cursor.fetchall()
        logger.debug(f"Raw data fetched: {data}")
        
        # Handle case where there's no data
        if not data:
            logger.warning("No data found for player")
            chart = QChart()
            chart.setTitle("No performance data available")
            return QChartView(chart)
        
        try:
            months, avg_kills, avg_deaths, avg_assists, avg_revives, games, dates = zip(*reversed(data))
            logger.debug(f"\nProcessing monthly data:")
            logger.debug(f"Months: {months}")
            logger.debug(f"Games per month: {games}")
            logger.debug(f"Sample dates included: {dates}")
            
            # Format month labels with games count (simpler now)
            month_labels = [f"{m}\n({g} games)" for m, g in zip(months, games)]

            # Round the averages to whole numbers
            avg_kills = tuple(round(x) for x in avg_kills)
            avg_deaths = tuple(round(x) for x in avg_deaths)
            avg_assists = tuple(round(x) for x in avg_assists)
            avg_revives = tuple(round(x) for x in avg_revives)

            # Calculate actual max value from data
            max_value = max(max(avg_kills), max(avg_deaths), max(avg_assists), max(avg_revives))

            # Create and style bar sets with label colors
            kills_set = QBarSet("Avg Kills")
            deaths_set = QBarSet("Avg Deaths")
            assists_set = QBarSet("Avg Assists")
            revives_set = QBarSet("Avg Revives")

            # Set label colors for each bar set
            kills_set.setLabelColor(QColor("#000000"))
            deaths_set.setLabelColor(QColor("#000000"))
            assists_set.setLabelColor(QColor("#000000"))
            revives_set.setLabelColor(QColor("#000000"))

            # Add data to sets
            kills_set.append(avg_kills)
            deaths_set.append(avg_deaths)
            assists_set.append(avg_assists)
            revives_set.append(avg_revives)

            # Create and configure series with tooltips
            series = QBarSeries()
            series.append(kills_set)
            series.append(deaths_set)
            series.append(assists_set)
            series.append(revives_set)
            series.setBarWidth(0.5)
            series.setLabelsVisible(True)
            series.setLabelsPosition(QBarSeries.LabelsOutsideEnd)
            series.setLabelsFormat("@value")
            
            # Add hover effects and tooltips
            def on_hover(status, index, barset):
                if status:  # Mouse entered
                    tooltip = f"{barset.label()}\nValue: {barset.at(index)}\nMonth: {month_labels[index]}"
                    QToolTip.showText(QCursor.pos(), tooltip)
                else:  # Mouse left
                    QToolTip.hideText()

            series.hovered.connect(on_hover)

            # Create and style chart with compact title
            chart = QChart()
            chart.addSeries(series)
            chart.setTitle("Monthly Performance Trends")
            title_font = QFont("Arial", 10, QFont.Bold)
            chart.setTitleFont(title_font)
            chart.setAnimationOptions(QChart.SeriesAnimations)
            
            # Set chart theme and background with reduced margins
            chart.setBackgroundVisible(False)
            chart.setPlotAreaBackgroundVisible(True)
            chart.setPlotAreaBackgroundBrush(QBrush(QColor("#f8f9fa")))
            chart.setBackgroundRoundness(0)
            chart.setMargins(QMargins(10, 5, 10, 0))
            
            # Create and style Y-axis with better readability
            axis_y = QValueAxis()
            axis_y.setTitleText("Average Count")
            axis_y.setTitleFont(QFont("Arial", 10, QFont.Bold))
            
            # Calculate nice round numbers for ticks
            max_value = int(max_value)  # Ensure integer
            if max_value <= 10:
                tick_interval = 2
                max_tick = 10
            elif max_value <= 20:
                tick_interval = 4
                max_tick = 20
            elif max_value <= 50:
                tick_interval = 10
                max_tick = ((max_value + 9) // 10) * 10
            else:
                tick_interval = 20
                max_tick = ((max_value + 19) // 20) * 20
            
            # Set Y-axis properties
            axis_y.setRange(0, max_tick)
            axis_y.setTickCount(max_tick // tick_interval + 1)
            axis_y.setMinorTickCount(1)  # Add minor ticks for better readability
            axis_y.setLabelFormat("%d")  # Whole numbers only
            
            # Style Y-axis
            axis_y.setLabelsFont(QFont("Arial", 9, QFont.Bold))
            axis_y.setLabelsColor(QColor("#000000"))
            axis_y.setGridLineColor(QColor("#e0e0e0"))
            axis_y.setMinorGridLineVisible(False)  # Hide minor grid lines
            axis_y.setGridLineVisible(True)
            
            # Add some padding to ensure labels are visible
            chart.setMargins(QMargins(20, 10, 10, 10)) 
            
            chart.addAxis(axis_y, Qt.AlignLeft)
            series.attachAxis(axis_y)

            # Create and style X-axis
            axis_x = QBarCategoryAxis()
            axis_x.append(month_labels)
            axis_x.setLabelsFont(QFont("Arial", 9))
            axis_x.setGridLineVisible(False)
            chart.addAxis(axis_x, Qt.AlignBottom)
            series.attachAxis(axis_x)

            # Configure legend with reduced spacing
            chart.legend().setVisible(True)
            chart.legend().setAlignment(Qt.AlignBottom)
            chart.legend().setFont(QFont("Arial", 9))
            chart.legend().setMarkerShape(QLegend.MarkerShapeRectangle)
            chart.legend().setContentsMargins(0, 0, 0, 0)  # Minimize legend margins
            
            # Create chart view with adjusted height and resize handling
            settings = QSettings('DeltaForce', 'Leaderboard')
            chart_view = ResizableChartView(chart, settings)
            chart_view.setRenderHint(QPainter.Antialiasing)
            
            # Restore saved height or use default
            saved_height = settings.value('chartGroupHeight', 50)
            chart_view.setFixedHeight(int(saved_height))
            
            return chart_view
            
        except Exception as e:
            logger.error(f"Error creating chart components: {str(e)}", exc_info=True)
            raise
            
    except Exception as e:
        logger.error(f"Error in chart creation: {str(e)}", exc_info=True)
        chart = QChart()
        chart.setTitle("Error creating chart")
        return QChartView(chart)

def setup_overall_tab(dialog):
    settings = QSettings('DeltaForce', 'Leaderboard')
    layout = QVBoxLayout()
    
    # Create monthly performance chart
    with sqlite3.connect(dialog.parent.db.db_path) as conn:
        cursor = conn.cursor()
        performance_chart = create_monthly_performance_chart(cursor, dialog.player_name)
        
        # Add chart to layout in a group box with adjusted height
        chart_group = QGroupBox("Monthly Performance")
        chart_layout = QVBoxLayout()
        chart_layout.setContentsMargins(5, 5, 5, 5)
        
        # Restore saved chart height or use default
        saved_height = settings.value('chartGroupHeight', 250)
        performance_chart.setFixedHeight(int(saved_height))
        
        chart_layout.addWidget(performance_chart)
        chart_group.setLayout(chart_layout)
        layout.addWidget(chart_group)

    summary_group = QGroupBox("Overall Statistics")
    summary_layout = QGridLayout()
    
    db = dialog.parent.db
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        # Add favorite class query
        cursor.execute(QUERY_FAVORITE_CLASS, (dialog.player_name,))
        favorite_class = cursor.fetchone()
        
        # Get class distribution
        cursor.execute("""
            SELECT 
                class,
                COUNT(*) as count,
                ROUND(CAST(COUNT(*) AS FLOAT) * 100 / 
                    (SELECT COUNT(*) FROM matches WHERE player_name = ?), 1) as percentage
            FROM matches
            WHERE player_name = ?
            GROUP BY class
        """, (dialog.player_name, dialog.player_name))
        raw_class_stats = {cls: (count, pct) for cls, count, pct in cursor.fetchall()}
        
        # Create full class stats including zeros for missing classes
        class_stats = []
        for class_name in PLAYER_CLASSES:
            if (class_name in raw_class_stats):
                count, pct = raw_class_stats[class_name]
                class_stats.append((class_name, count, pct))
            else:
                class_stats.append((class_name, 0, 0.0))
        
        # Add victory/defeat count query
        cursor.execute(QUERY_VICTORY_STATS, (dialog.player_name,))
        victory_stats = cursor.fetchone()
        
        # Get overall stats
        cursor.execute(QUERY_PLAYER_STATS, (dialog.player_name,))
        stats = cursor.fetchone()
        
        # Create stat groups dictionary with proper null handling
        stat_groups = {
            "Player Info": [
                ("Favorite Class:", favorite_class[0] if favorite_class else "N/A"),
                ("Total Games:", stats[0] if stats else 0),
                *[(f"{class_name} Games:", f"{count} ({pct}%)")
                  for class_name, count, pct in class_stats],
            ],
            "Match Results": [
                ("Victories:", victory_stats[0] if victory_stats else 0),
                ("Defeats:", victory_stats[1] if victory_stats else 0),
                ("Win Rate:", f"{(victory_stats[0]/(victory_stats[0] + victory_stats[1])*100):.1f}%" if victory_stats and (victory_stats[0] + victory_stats[1]) > 0 else "0%"),
                ("Average Rank:", stats[15] if stats else 0),
            ],
            "Combat Stats": [
                ("Total Score:", stats[1] if stats else 0),
                ("Average Score:", stats[2] if stats else 0),
                ("Best Score:", stats[3] if stats else 0),
            ],
            "Combat Performance": [
                ("Total Kills:", stats[4] if stats else 0),
                ("Average Kills:", stats[5] if stats else 0),
                ("Total Deaths:", stats[6] if stats else 0),
                ("Average Deaths:", stats[7] if stats else 0),
                ("K/D Ratio:", stats[8] if stats else "0.00"),
            ],
            "Support Stats": [
                ("Total Assists:", stats[9] if stats else 0),
                ("Average Assists:", stats[10] if stats else 0),
                ("Total Revives:", stats[11] if stats else 0),
                ("Average Revives:", stats[12] if stats else 0),
            ],
            "Objective Stats": [
                ("Total Captures:", stats[13] if stats else 0),
                ("Average Captures:", stats[14] if stats else 0),
            ]
        }

        # Create stat boxes
        row = 0
        for group_name, group_stats in stat_groups.items():
            group_box = QGroupBox(group_name)
            group_layout = QGridLayout()
            
            for i, (label, value) in enumerate(group_stats):
                group_layout.addWidget(QLabel(label), i, 0)
                formatted_value = dialog.format_value(value, label)
                group_layout.addWidget(QLabel(formatted_value), i, 1)
            
            group_box.setLayout(group_layout)
            summary_layout.addWidget(group_box, row // 2, row % 2)
            row += 1

    summary_group.setLayout(summary_layout)
    layout.addWidget(summary_group)
    
    dialog.overall_tab.setLayout(layout)
