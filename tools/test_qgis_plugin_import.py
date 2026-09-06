import sys
sys.path.insert(0, r"c:\Users\lefpa\Downloads\QGIS-AI")
try:
    import stratum_ro
    from stratum_ro.stratum_ro import StratumRO
    print("StratumRO import success in QGIS Python!")
except Exception as e:
    import traceback
    traceback.print_exc()
