class CurveData:
    """Класс-заглушка для совместимости, если данные хранятся просто в списке."""
    def __init__(self, data=None):
        self.data = data if data is not None else []

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        return self.data[index]

    def __repr__(self):
        return f"CurveData(len={len(self.data)})"
