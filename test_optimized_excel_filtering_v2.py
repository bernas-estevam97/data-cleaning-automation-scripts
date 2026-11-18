# Self-check for optimized_excel_filtering_v2.kinematics_from_positions. Run: python test_optimized_excel_filtering_v2.py
import numpy as np
import pandas as pd
from optimized_excel_filtering_v2 import kinematics_from_positions

t = np.arange(200) * 0.01
# Hind left paw: rests, then one fast 4 cm swing (peak ~1 m/s), then rests. The old Kinematics sheet clipped this peak.
swing = 0.02 * (1 - np.cos(np.pi * np.clip((t - 1.0) / 0.08, 0, 1)))
pos = pd.DataFrame({
    'Time': t,
    '/Feature/Paw/Hind/Left_X': swing, '/Feature/Paw/Hind/Left_Y': np.zeros_like(t),
    '/Feature/Paw/Front/Left_X': np.full_like(t, 0.05), '/Feature/Paw/Front/Left_Y': np.zeros_like(t),
    '/Feature/PSIS/Left_X': np.zeros_like(t), '/Feature/PSIS/Left_Y': np.full_like(t, 0.03),
    '/Feature/Hip/Left_X': np.zeros_like(t), '/Feature/Hip/Left_Y': np.zeros_like(t),
    '/Feature/Knee/Left_X': np.full_like(t, 0.02), '/Feature/Knee/Left_Y': np.zeros_like(t),
})
sheet = pd.DataFrame({'Time': t, 'Step Length (Left)': 0.0, 'Hip Angle (Left)': 0.0,
                      'Hip Left Speed (m/s)': 0.0, 'Hind Left Speed (m/s)': 0.0, 'Unknown Metric': 7.0})
out, kept = kinematics_from_positions(pos, sheet)

assert list(out.columns) == list(sheet.columns)
assert kept == ['Hip Left Speed (m/s)', 'Unknown Metric'], kept          # no formula: kept from the sheet
assert (out['Unknown Metric'] == 7.0).all()
assert np.isclose(out['Step Length (Left)'].iloc[0], 0.05) and np.isclose(out['Step Length (Left)'].iloc[-1], 0.01)
assert np.allclose(out['Hip Angle (Left)'], 90)
peak = out['Hind Left Speed (m/s)'].max()
assert 0.6 < peak < 0.8, peak                                              # true peak = 0.04*pi/(2*0.08) ~ 0.79
assert out['Hind Left Speed (m/s)'].iloc[:90].abs().max() < 1e-9           # resting paw = 0 speed
print('ok')
