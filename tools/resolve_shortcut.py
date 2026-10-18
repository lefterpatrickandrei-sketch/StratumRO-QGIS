import os
try:
    import win32com.client
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\TransDatRO 4.08.lnk")
    print("Target path:", shortcut.Targetpath)
    print("Working dir:", shortcut.WorkingDirectory)
except Exception as e:
    print("Error with win32com:", e)
    # Alternative: parse binary .lnk or use powershell script file
