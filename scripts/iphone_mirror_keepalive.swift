import Foundation
import AppKit
import CoreGraphics
import IOKit.pwr_mgt

final class IPhoneMirrorKeepAlive {
    private var assertionID: IOPMAssertionID = 0
    private var isAssertionActive = false
    private let interval: TimeInterval
    private let swipeDistance: CGFloat
    private let maxDuration: TimeInterval
    private let openAppOnStart: Bool
    private var isRunning = true

    init(interval: TimeInterval = 20.0, swipeDistance: CGFloat = 40.0, maxDuration: TimeInterval = 0.0, openAppOnStart: Bool = true) {
        self.interval = interval
        self.swipeDistance = swipeDistance
        self.maxDuration = maxDuration
        self.openAppOnStart = openAppOnStart
    }

    func start() {
        setupSignalHandlers()
        acquirePowerAssertion()

        print("=== Google Photos Backup — iPhone Keep-Alive ===")
        print("Interval: \(Int(interval))s | Swipe Distance: \(Int(swipeDistance))px")
        if maxDuration > 0 {
            print("Auto-stop after: \(Int(maxDuration / 60)) minutes")
        } else {
            print("Running indefinitely. Press Ctrl+C to stop.")
        }
        print("--------------------------------------------------")

        if openAppOnStart {
            openGooglePhotosOnIPhone()
        }

        let startTime = Date()

        while isRunning {
            if maxDuration > 0 && Date().timeIntervalSince(startTime) >= maxDuration {
                print("Specified duration reached. Stopping.")
                break
            }

            performKeepAliveCycle()
            Thread.sleep(forTimeInterval: interval)
        }

        cleanup()
    }

    private func openGooglePhotosOnIPhone() {
        print("[\(currentTimestamp())] Searching and opening Google Photos on iPhone...")
        let script = """
        tell application "iPhone Mirroring" to activate
        delay 0.5
        tell application "System Events"
            tell process "iPhone Mirroring"
                try
                    click menu item "Spotlight" of menu 1 of menu bar item "View" of menu bar 1
                    delay 0.6
                    keystroke "Google Photos"
                    delay 1.0
                    key code 36
                end try
            end tell
        end tell
        """
        var error: NSDictionary?
        if let appleScript = NSAppleScript(source: script) {
            appleScript.executeAndReturnError(&error)
        }
        Thread.sleep(forTimeInterval: 2.0)
    }

    func stop() {
        isRunning = false
    }

    private func setupSignalHandlers() {
        signal(SIGINT) { _ in
            print("\nReceived stop signal. Cleaning up...")
            KeepAliveManager.sharedInstance?.stop()
        }
        signal(SIGTERM) { _ in
            print("\nReceived termination signal. Cleaning up...")
            KeepAliveManager.sharedInstance?.stop()
        }
    }

    private func acquirePowerAssertion() {
        let reason = "Google Photos Backup Keep Alive via iPhone Mirroring" as CFString
        let result = IOPMAssertionCreateWithName(
            kIOPMAssertionTypePreventUserIdleDisplaySleep as CFString,
            IOPMAssertionLevel(kIOPMAssertionLevelOn),
            reason,
            &assertionID
        )

        if result == kIOReturnSuccess {
            isAssertionActive = true
            print("[\(currentTimestamp())] Sleep prevention assertion active.")
        } else {
            print("[\(currentTimestamp())] [Warning] Could not acquire sleep prevention assertion.")
        }
    }

    private func releasePowerAssertion() {
        guard isAssertionActive else { return }
        IOPMAssertionRelease(assertionID)
        isAssertionActive = false
        print("[\(currentTimestamp())] Sleep prevention assertion released.")
    }

    private func cleanup() {
        releasePowerAssertion()
        print("[\(currentTimestamp())] Keep-Alive stopped.")
    }

    private func findIPhoneMirroringWindow() -> CGRect? {
        let options: CGWindowListOption = [.optionOnScreenOnly, .excludeDesktopElements]
        guard let windowList = CGWindowListCopyWindowInfo(options, kCGNullWindowID) as? [[String: Any]] else {
            return nil
        }

        for win in windowList {
            guard let owner = win[kCGWindowOwnerName as String] as? String,
                  owner == "iPhone Mirroring" || owner == "iPhone Yansıtma" else {
                continue
            }

            if let bounds = win[kCGWindowBounds as String] as? [String: Any],
               let x = bounds["X"] as? Double,
               let y = bounds["Y"] as? Double,
               let w = bounds["Width"] as? Double,
               let h = bounds["Height"] as? Double,
               w > 200 && h > 400 {
                return CGRect(x: x, y: y, width: w, height: h)
            }
        }
        return nil
    }

    private func activateAppIfNeeded() {
        let apps = NSWorkspace.shared.runningApplications.filter {
            $0.bundleIdentifier == "com.apple.ScreenContinuity" || $0.localizedName == "iPhone Mirroring"
        }
        if let app = apps.first, !app.isActive {
            app.activate()
        }
    }

    private func performKeepAliveCycle() {
        guard let windowRect = findIPhoneMirroringWindow() else {
            print("[\(currentTimestamp())] iPhone Mirroring window not detected. Launching/activating...")
            activateAppIfNeeded()
            return
        }

        let originalMousePos = CGEvent(source: nil)?.location

        let centerX = windowRect.midX
        let startY = windowRect.midY + (swipeDistance / 2.0)
        let endY = windowRect.midY - (swipeDistance / 2.0)

        let startPoint = CGPoint(x: centerX, y: startY)
        let endPoint = CGPoint(x: centerX, y: endY)

        simulateSwipe(from: startPoint, to: endPoint)

        if let orig = originalMousePos {
            CGWarpMouseCursorPosition(orig)
        }

        print("[\(currentTimestamp())] Kept alive: subtle swipe up on iPhone window (\(Int(windowRect.origin.x)), \(Int(windowRect.origin.y)))")
    }

    private func simulateSwipe(from start: CGPoint, to end: CGPoint) {
        let source = CGEventSource(stateID: .combinedSessionState)

        let steps = 5
        let deltaY = (end.y - start.y) / CGFloat(steps)

        let mouseDown = CGEvent(mouseEventSource: source, mouseType: .leftMouseDown, mouseCursorPosition: start, mouseButton: .left)
        mouseDown?.post(tap: CGEventTapLocation.cghidEventTap)
        usleep(30_000)

        for i in 1...steps {
            let intermediateY = start.y + (deltaY * CGFloat(i))
            let currentPt = CGPoint(x: start.x, y: intermediateY)
            let mouseDrag = CGEvent(mouseEventSource: source, mouseType: .leftMouseDragged, mouseCursorPosition: currentPt, mouseButton: .left)
            mouseDrag?.post(tap: CGEventTapLocation.cghidEventTap)
            usleep(25_000)
        }

        let mouseUp = CGEvent(mouseEventSource: source, mouseType: .leftMouseUp, mouseCursorPosition: end, mouseButton: .left)
        mouseUp?.post(tap: CGEventTapLocation.cghidEventTap)
        usleep(30_000)
    }

    private func currentTimestamp() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm:ss"
        return formatter.string(from: Date())
    }
}

enum KeepAliveManager {
    static var sharedInstance: IPhoneMirrorKeepAlive?
}

var interval: TimeInterval = 20.0
var swipeDist: CGFloat = 40.0
var duration: TimeInterval = 0.0
var openAppOnStart = true

let args = CommandLine.arguments
var index = 1
while index < args.count {
    switch args[index] {
    case "--interval", "-i":
        if index + 1 < args.count, let val = Double(args[index + 1]) {
            interval = max(5.0, val)
            index += 1
        }
    case "--distance", "-d":
        if index + 1 < args.count, let val = Double(args[index + 1]) {
            swipeDist = CGFloat(val)
            index += 1
        }
    case "--duration", "-t":
        if index + 1 < args.count, let val = Double(args[index + 1]) {
            duration = val * 60.0
            index += 1
        }
    case "--no-open":
        openAppOnStart = false
    case "--help", "-h":
        print("""
        Usage: iphone_mirror_keepalive [options]
        
        Options:
          -i, --interval <seconds>    Interval between swipe events (default: 20s)
          -d, --distance <pixels>     Vertical swipe distance in pixels (default: 40px)
          -t, --duration <minutes>    Run duration in minutes (default: 0 = indefinite)
              --no-open               Skip auto-searching and opening Google Photos
          -h, --help                  Show this help message
        """)
        exit(0)
    default:
        break
    }
    index += 1
}

let keepAlive = IPhoneMirrorKeepAlive(interval: interval, swipeDistance: swipeDist, maxDuration: duration, openAppOnStart: openAppOnStart)
KeepAliveManager.sharedInstance = keepAlive
keepAlive.start()
