# Inbox

For documents you import from elsewhere — old .docx character bios, .rtf
chapter drafts, .html research saves.

You don't drop files here manually. The `worldcanon-import.exe` program
that came with your install does it for you.

## Quick import flow

1. Open PowerShell (Start menu → type "PowerShell")
2. Run:
   ```
   cd %LOCALAPPDATA%\WorldbuilderCanon
   worldcanon-import.exe --source "C:\path\to\your\old\docs" --dest "C:\path\to\this-vault\_inbox"
   ```
3. Back in Obsidian, run `Canon: Triage inbox`
4. For each imported note, the plugin proposes: "this looks like a
   character sheet" or "this looks like prose" — confirm or override

You can delete this note once you've imported what you need (or if
you're starting fresh and have nothing to import).
