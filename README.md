# Seneca downloads

Seneca is my desktop study companion: an ivory-and-gold droid with an ancient-futuristic, cyberpunk-inspired design. I’m Sebastian Canales, Seneca’s original artist and art rights holder.

**[Download the latest release](https://github.com/sebasnyc/project-seneca-downloads/releases/latest)**

Seneca 0.14.0 refreshes the desktop with ivory, gold, and teal, Oxanium titles, and Atkinson Hyperlegible Next for buttons and reading. Mainframe adapts to narrow windows, topic changes keep your draft, and School Day lets you double-click an empty slot to add a class or study block. [0.14.0 release notes](release-notes/0.14.0.md)

Under **Assets**, choose **Setup.exe** to install, or the complete **Portable.zip** for a portable Windows copy. For Mac, choose **macOS-arm64.zip** (Apple Silicon) or **macOS-x86_64.zip** (Intel), expand it and move Seneca.app to Applications. Both Mac downloads require macOS 14 or newer and passed their frozen-app checks. No Python or Node installation is needed. Builds are unsigned prototypes, so Windows may show a publisher/reputation warning.

Installed copies from 0.7.2 onward can check, download and install verified updates from this public repo while idle. Your Windows-protected connections, keys, chat, drafts and settings stay on your PC, outside the install directory. Help & About → Updates provides the controls. Quit older copies before updating manually; portable copies require manual replacement.

Version 0.11 adds a local second brain: linked notes/backlinks, tags, selected source associations, original/recent versions, separate tutor interpretations, topic maps, visual boards, JSON Canvas/Markdown interchange and a dated learning timeline. Note-specific tutor conversations keep other drafts saved and require explicit review before cloud sharing.

School day adds manual/local-file timetables, after-class check-ins, shared assignment checklist/board/calendar views and reviewed catch-up plans that avoid classes while keeping actual deadlines intact. Calendar imports cover a bounded 16-week range and report unsupported events. Personal touches adds restrained accents, saved resting poses and optional effort milestones. New study collections and unfinished drafts stay in the protected profile and password backups. No paid API is needed for local organization/planning.

Version 0.10.1 simplifies the menu into four daily actions, with grouped preferences and a separate Help & About panel. Continue studying returns to the last course or conversation. Movement controls and course import/export actions are tucked away until needed.

Version 0.10 brings a course home with notes, glossary, pinned answers, learning preferences and checkpoints; exam plans, rubrics and text/drawing scratchpads; revision/shared study packs; subject/topic deletion with Undo; weekly activity summaries; local search and Ctrl+K actions; Quiet Study, reminder quiet hours and text sizing. Portable backups now default to password encryption and still exclude saved connections/keys.

Course videos offer free public YouTube search without a mandatory API key or AI credits, selected-link checks, official player/browser playback and saved Mark watched status. If YouTube blocks or changes its page, browser search and manual links remain available. Seneca does not invent replacement links or monitor the screen.

Privacy controls redact recognizable private text before cloud AI review and offer a strict Local-only AI setting. Cloud audio defaults off; Groq free-tier transcription needs its own key, explicit privacy opt-in and recording review. Local problem reports open public GitHub drafts only after review; the user still submits them in the browser.

The companion is 20% smaller with softer ivory/gold shading, solar teleport effects and bottom-taskbar perching. New profiles have gentle sounds on, with a remembered mute and temporary Quiet Study muting.

Avatar quick chat, subject/topic workspaces, selected documents and citations, deadlines/plans, quizzes/flashcards, optional activity XP, Fish Audio/speaker choice, local security checks and installed sign-in startup remain available.

This repo contains release downloads, notices and publishing infrastructure. Seneca’s application source development stays private. Team members can install and test public downloads without access to the source repo. Please avoid including API keys or personal chat content in issue reports.

Seneca uses **PolyForm Noncommercial 1.0.0**, with the required Sebastian Canales copyright and Seneca project-credit notices. See [LICENSE.md](LICENSE.md), [NOTICE.txt](NOTICE.txt), and the third-party notices bundled with each app download.

Automated Windows Server checks do not replace hands-on Windows 11 DPI/perching, audio hardware or tutoring-quality testing.

## macOS (0.11.1 onward)

Requires macOS 14+. Mac downloads contain the same student features as Windows. Help & About → Updates checks the exact processor-specific ZIP and verifies it before saving; quit and replace the app manually. Windows continues selecting only its Setup.exe. Saved Mac profiles are AES-GCM encrypted outside the bundle under ~/Library/Application Support/Seneca, with the key in Keychain; replacing the app preserves data. A new unsigned build may request Keychain access again.

Mac prototypes are ad-hoc signed, not Developer ID signed or notarized. Review System Settings → Privacy & Security → Open Anyway if blocked; never disable Gatekeeper. Enable login startup only after moving the app to Applications. Windows-only taskbar/window perching, global shortcut and Defender/network queries are unavailable. Live voice and physical Mac acceptance remain manual checks.

The same verified Windows x64, Apple Silicon, and Intel downloads are also archived in the original private repo. Platform/processor-specific updater checks passed; Windows continues to select only its Windows installer.
