from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtCore import Qt

class NumericSortItem(QTableWidgetItem):
    def __init__(self, value):
        super().__init__(str(value))
        if isinstance(value, str) and '%' in value:
            # Extract numeric value from percentage string
            self._value = float(value.strip('%'))
        else:
            # Convert to float or use 0.0 if conversion fails
            try:
                self._value = float(value)
            except (ValueError, TypeError):
                self._value = 0.0
        
        self.setTextAlignment(Qt.AlignCenter)

    def __lt__(self, other):
        if isinstance(other, NumericSortItem):
            return self._value < other._value
        return super().__lt__(other)
