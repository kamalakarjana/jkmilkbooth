import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import build_yearly_monthly_summary


def test_yearly_summary_has_twelve_months():
    summary = build_yearly_monthly_summary(2026)
    assert isinstance(summary, list)
    assert len(summary) == 12
    assert all('month' in item for item in summary)
    assert all('profit_loss' in item for item in summary)


if __name__ == '__main__':
    test_yearly_summary_has_twelve_months()
    print('dashboard summary test passed')
