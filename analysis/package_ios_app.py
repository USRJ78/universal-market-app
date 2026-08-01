"""
==============================================================================
  NATIVE iOS APP PACKAGING & DEPLOYMENT GUIDE (SWARM ALPHA V6.0)
==============================================================================
  Provides the exact blueprint for compiling a native iOS App (.ipa)
  or setting up Progressive Web App (PWA) on iPhone.
==============================================================================
"""

import os, sys

def main():
    print("=" * 75)
    print("  SWARM ALPHA V6.0 — NATIVE iOS APP PACKAGING & DEPLOYMENT GUIDE")
    print("=" * 75)
    print("\n  METHOD 1: INSTANT NATIVE PWA (RECOMMENDED - 0 APPSTORE FEES)")
    print("  -------------------------------------------------------------")
    print("  Apple iOS supports Progressive Web Apps (PWA) natively.")
    print("  When you add SwarmAlpha to your iPhone Home Screen:")
    print("  1. Open Safari on iPhone -> Go to: http://192.168.1.16:8080")
    print("  2. Tap Share Button (bottom square with arrow up)")
    print("  3. Tap 'Add to Home Screen'")
    print("  Result: Removes all Safari browser bars. Launches as a full-screen,")
    print("          standalone native app with a custom app icon on your home screen!\n")

    print("  METHOD 2: COMPILED NATIVE iOS APP (.IPA / XCODE / SIDELOADLY)")
    print("  -------------------------------------------------------------")
    print("  To build an actual compiled iOS App (.ipa) using Capacitor:")
    print("  1. Install Node.js & Capacitor:")
    print("     npm install @capacitor/core @capacitor/cli @capacitor/ios")
    print("  2. Initialize Capacitor:")
    print("     npx cap init SwarmAlpha com.swarmalpha.app --web-dir ../web_app")
    print("  3. Add iOS platform:")
    print("     npx cap add ios")
    print("  4. Open in Xcode & Build .ipa:")
    print("     npx cap open ios")
    print("  5. Install via AltStore, Sideloadly, or TestFlight on your iPhone.")
    print("=" * 75)

if __name__ == "__main__":
    main()
