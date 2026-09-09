package com.mohmb142.phoneagent

import android.accessibilityservice.AccessibilityService
import android.view.accessibility.AccessibilityEvent

class PhoneAccessibilityService : AccessibilityService() {
    companion object { var instance: PhoneAccessibilityService? = null }
    override fun onServiceConnected() { super.onServiceConnected(); instance = this }
    override fun onAccessibilityEvent(event: AccessibilityEvent?) {}
    override fun onInterrupt() {}
    override fun onDestroy() { if (instance === this) instance = null; super.onDestroy() }
}
