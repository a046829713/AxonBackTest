import copy
import time
from typing import Any, Dict, List, Optional, Sequence, Union

import matplotlib.pyplot as plt
from matplotlib.widgets import Button, CheckButtons
import numpy as np
import pandas as pd

import AxonBackTest.config as config
from AxonBackTest.PorfolioTrader import PortfolioManagement
from AxonBackTest.strategy import Strategy


class BackTester:
    def __init__(self, manager: PortfolioManagement = None):
        """
        Operator for the backtest execution and visualization process.

        Args:
            manager (PortfolioManagement, optional): Portfolio manager instance. Defaults to None.
        """
        self.pfm = manager
        self.report = None

    def generate_report(self):
        """Generates backtest performance records from portfolio management."""
        self.report = self.pfm.generate_report()
        return self.report

    def _prepare_report_df(self) -> pd.DataFrame:
        """
        Validates report presence and converts it into a DatetimeIndexed DataFrame.

        Returns:
            pd.DataFrame indexed by Datetime.
        """
        if self.report is None:
            self.generate_report()

        if not self.report:
            raise ValueError("Report data is empty; cannot render plots.")

        report_df = pd.DataFrame(self.report)
        report_df["datetimelist"] = pd.to_datetime(report_df["datetimelist"])
        report_df.set_index("datetimelist", inplace=True)
        report_df.index.name = "Datetime"
        return report_df

    def plot_performance(self, show: bool = True) -> plt.Figure:
        """
        Renders the portfolio performance figure with two stacked subplots:
        1. Top: Mark-to-Market Equity over time.
        2. Bottom: Realized CloseProfit cash balance over time.

        Args:
            show: If True, calls plt.show() immediately.

        Returns:
            plt.Figure: The created figure instance.
        """
        report_df = self._prepare_report_df()
        plt.style.use("seaborn-v0_8-darkgrid")

        fig, (ax_equity, ax_close) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)
        if fig.canvas.manager is not None:
            fig.canvas.manager.set_window_title("Portfolio Equity & Close Profit")

        if "Equity" in report_df.columns:
            ax_equity.plot(
                report_df.index,
                report_df["Equity"],
                label="Equity (Mark-to-Market)",
                color="#1f77b4",
                linewidth=1.2,
            )
            ax_equity.legend(loc="best", frameon=True, facecolor="white", framealpha=0.8)
        ax_equity.set_title("Portfolio Equity Over Time (Mark-to-Market)", fontsize=14)
        ax_equity.set_ylabel("Equity (USD)", fontsize=12)
        ax_equity.grid(True)

        if "CloseProfit" in report_df.columns:
            ax_close.plot(
                report_df.index,
                report_df["CloseProfit"],
                label="CloseProfit (Realized Cash)",
                color="#2ca02c",
                linewidth=1.2,
                drawstyle="steps-post",
            )
            ax_close.legend(loc="best", frameon=True, facecolor="white", framealpha=0.8)
        ax_close.set_title("Portfolio Close Profit Over Time (Realized)", fontsize=14)
        ax_close.set_xlabel("Date", fontsize=12)
        ax_close.set_ylabel("Close Profit (USD)", fontsize=12)
        ax_close.grid(True)
        fig.tight_layout()

        if show:
            plt.show()
        return fig

    def plot_positions(
        self,
        symbols: Optional[Union[str, Sequence[str]]] = None,
        interactive: bool = True,
        show: bool = True,
    ) -> Optional[plt.Figure]:
        """
        Renders strategy target position ratios over time.

        Args:
            symbols: Optional single symbol string or sequence of symbols/strategies to filter.
            interactive: If True, enables interactive GUI checkboxes, All/None buttons, and clickable legend.
            show: If True, calls plt.show() immediately.

        Returns:
            Optional[plt.Figure]: The created figure instance or None if no position columns exist.
        """
        report_df = self._prepare_report_df()
        plt.style.use("seaborn-v0_8-darkgrid")

        pos_cols = [col for col in report_df.columns if col.startswith("pos_")]
        if not pos_cols:
            print("No position columns (pos_*) found in report.")
            return None

        # Filter by symbols/strategies if provided
        if symbols is not None:
            if isinstance(symbols, str):
                target_symbols = {symbols.strip().lower()}
            else:
                target_symbols = {str(s).strip().lower() for s in symbols}

            filtered_cols = []
            for col in pos_cols:
                raw_name = col.removeprefix("pos_").lower()
                if (
                    col.lower() in target_symbols
                    or raw_name in target_symbols
                    or any(raw_name.startswith(t) or t in raw_name for t in target_symbols)
                ):
                    filtered_cols.append(col)

            if not filtered_cols:
                print(
                    f"Warning: No matching position columns found for filter: {symbols}. "
                    f"Available: {[c.removeprefix('pos_') for c in pos_cols]}"
                )
                filtered_cols = pos_cols
            pos_cols = filtered_cols

        fig, ax_pos = plt.subplots(figsize=(16, 6))
        if fig.canvas.manager is not None:
            fig.canvas.manager.set_window_title("Portfolio Target Positions")

        lines_by_label: Dict[str, Any] = {}
        for col in pos_cols:
            strategy_label = col.removeprefix("pos_")
            (line,) = ax_pos.plot(
                report_df.index,
                report_df[col],
                label=strategy_label,
                linewidth=1.2,
                drawstyle="steps-post",
            )
            lines_by_label[strategy_label] = line

        ax_pos.axhline(0.0, color="gray", linestyle="--", linewidth=0.8, alpha=0.7)
        ax_pos.set_title("Strategy Target Position Ratio Over Time", fontsize=14)
        ax_pos.set_xlabel("Date", fontsize=12)
        ax_pos.set_ylabel("Position Ratio", fontsize=12)
        leg = ax_pos.legend(loc="upper left", frameon=True, facecolor="white", framealpha=0.8)
        ax_pos.grid(True)

        # Interactive controls (CheckButtons, All/None buttons, Pickable Legend)
        interactive_widgets = []
        if interactive and len(lines_by_label) > 1:
            # Leave space on the right side for controls
            fig.subplots_adjust(left=0.08, right=0.78, top=0.92, bottom=0.10)

            # Quick Toggle Buttons: [All] and [None]
            ax_btn_all = fig.add_axes([0.81, 0.90, 0.075, 0.04])
            ax_btn_none = fig.add_axes([0.895, 0.90, 0.075, 0.04])
            btn_all = Button(ax_btn_all, "All", color="#e0e0e0", hovercolor="#c0c0c0")
            btn_none = Button(ax_btn_none, "None", color="#e0e0e0", hovercolor="#c0c0c0")

            # CheckButtons panel
            labels = list(lines_by_label.keys())
            actives = [True] * len(labels)

            cb_height = min(0.75, max(0.20, 0.035 * len(labels) + 0.05))
            ax_check = fig.add_axes([0.81, max(0.08, 0.88 - cb_height), 0.16, cb_height])
            check = CheckButtons(ax_check, labels, actives)
            for label_text in check.labels:
                label_text.set_fontsize(8)

            def set_all_visibility(target_visible: bool):
                for i, is_active in enumerate(check.get_status()):
                    if is_active != target_visible:
                        check.set_active(i)

            def on_check_clicked(label: str):
                line = lines_by_label[label]
                line.set_visible(not line.get_visible())
                _update_legend_styles()
                fig.canvas.draw_idle()

            def _update_legend_styles():
                if leg is not None:
                    for text, l_line in zip(leg.get_texts(), leg.get_lines()):
                        name = text.get_text()
                        if name in lines_by_label:
                            vis = lines_by_label[name].get_visible()
                            alpha = 1.0 if vis else 0.2
                            text.set_alpha(alpha)
                            l_line.set_alpha(alpha)

            btn_all.on_clicked(lambda event: set_all_visibility(True))
            btn_none.on_clicked(lambda event: set_all_visibility(False))
            check.on_clicked(on_check_clicked)

            # Interactive Legend picking
            if leg is not None:
                legend_map = {}
                for legline, legtext, label in zip(leg.get_lines(), leg.get_texts(), labels):
                    legline.set_picker(True)
                    legline.set_pickradius(5)
                    legtext.set_picker(True)
                    legend_map[legline] = label
                    legend_map[legtext] = label

                def on_pick(event):
                    artist = event.artist
                    if artist in legend_map:
                        label = legend_map[artist]
                        idx = labels.index(label)
                        check.set_active(idx)

                fig.canvas.mpl_connect("pick_event", on_pick)

            interactive_widgets.extend([btn_all, btn_none, check])
            # Keep references alive on figure to prevent garbage collection
            fig._interactive_widgets = interactive_widgets
        else:
            fig.tight_layout()

        if show:
            plt.show()
        return fig

    def plot_image(self) -> None:
        """
        Renders two standalone figures:
        1. Performance overview: Equity & CloseProfit.
        2. Target position ratios with interactive product filtering.
        """
        self.plot_performance(show=False)
        self.plot_positions(show=False)
        plt.show()

    def print_metrics(self):
        """Prints formatted statistical summary metrics."""
        print("=" * 50)
        print("          Portfolio Performance Metrics           ")
        print("=" * 50)
        for key, value in self.pfm.metrics.items():
            print(f"{key:25s}: {value}")
        print("=" * 50)