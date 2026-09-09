package com.mohmb142.phoneagent

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.provider.Settings
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.widget.*
import java.util.Locale

class MainActivity : Activity() {
    private lateinit var status: TextView
    private var recognizer: SpeechRecognizer? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val box = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(40,60,40,40) }
        val title = TextView(this).apply { text = "Phone Agent"; textSize = 28f }
        status = TextView(this).apply { text = "جاهز — اضغط الزر وتحدث"; textSize = 18f; setPadding(0,30,0,30) }
        val listen = Button(this).apply { text = "🎙️ استمع للأمر" }
        val access = Button(this).apply { text = "تفعيل صلاحية التحكم" }
        box.addView(title); box.addView(status); box.addView(listen); box.addView(access); setContentView(box)

        listen.setOnClickListener { startVoice() }
        access.setOnClickListener { startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)) }
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), 10)
    }

    private fun startVoice() {
        if (!SpeechRecognizer.isRecognitionAvailable(this)) { status.text = "التعرف الصوتي غير متاح على هذا الجهاز"; return }
        recognizer?.destroy()
        recognizer = SpeechRecognizer.createSpeechRecognizer(this).also { r ->
            r.setRecognitionListener(SimpleRecognitionListener { text -> handleCommand(text) })
            val i = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, "ar-SA")
                putExtra(RecognizerIntent.EXTRA_PROMPT, "تحدث بالأمر")
            }
            r.startListening(i); status.text = "أستمع..."
        }
    }

    private fun handleCommand(text: String) {
        status.text = "الأمر: $text"
        when {
            text.contains("الإعدادات") -> startActivity(Intent(Settings.ACTION_SETTINGS))
            text.contains("الرئيسية") -> PhoneAccessibilityService.instance?.performGlobalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_HOME)
            text.contains("رجوع") -> PhoneAccessibilityService.instance?.performGlobalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_BACK)
            text.contains("الإشعارات") -> PhoneAccessibilityService.instance?.performGlobalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_NOTIFICATIONS)
            else -> status.append("\nالأمر مفهوم، لكن هذا الإصدار لا ينفذه بعد.")
        }
    }

    override fun onDestroy() { recognizer?.destroy(); super.onDestroy() }
}

private class SimpleRecognitionListener(val onText: (String) -> Unit) : android.speech.RecognitionListener {
    override fun onResults(results: Bundle?) { val s = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull(); if (s != null) onText(s) }
    override fun onError(error: Int) {}
    override fun onReadyForSpeech(p: Bundle?) {}
    override fun onBeginningOfSpeech() {}
    override fun onRmsChanged(r: Float) {}
    override fun onBufferReceived(b: ByteArray?) {}
    override fun onEndOfSpeech() {}
    override fun onPartialResults(b: Bundle?) {}
    override fun onEvent(t: Int, p: Bundle?) {}
}
