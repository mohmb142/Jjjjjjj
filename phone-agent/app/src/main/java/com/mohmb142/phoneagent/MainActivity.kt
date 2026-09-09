package com.mohmb142.otcanalyzer

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.Gravity
import android.widget.*
import okhttp3.*
import java.io.IOException
import java.util.concurrent.TimeUnit

class MainActivity : Activity() {
    private val client = OkHttpClient.Builder().connectTimeout(30, TimeUnit.SECONDS).readTimeout(90, TimeUnit.SECONDS).build()
    private lateinit var apiUrl: EditText
    private lateinit var apiKey: EditText
    private lateinit var result: TextView
    private var imageUri: Uri? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER_HORIZONTAL; setPadding(28, 40, 28, 28) }
        val title = TextView(this).apply { text = "📊 Pocket OTC AI Analyzer"; textSize = 25f; gravity = Gravity.CENTER; setPadding(0, 0, 0, 18) }
        val safe = TextView(this).apply { text = "🔒 تحليل فقط — لا يتم تنفيذ أي صفقة"; textSize = 15f; gravity = Gravity.CENTER; setPadding(0, 0, 0, 18) }
        apiUrl = EditText(this).apply { hint = "رابط الخادم (مثال: https://...)"; setText(""); singleLine = true }
        apiKey = EditText(this).apply { hint = "OpenRouter API Key"; inputType = 0x81; singleLine = true }
        val pick = Button(this).apply { text = "📷 اختيار صورة الشارت" }
        val analyze = Button(this).apply { text = "🔎 تحليل الشارت"; isEnabled = false }
        result = TextView(this).apply { text = "اختر صورة واضحة ثم اضغط تحليل."; textSize = 16f; setPadding(0, 22, 0, 0); textIsSelectable = true }

        root.addView(title); root.addView(safe); root.addView(apiUrl, LinearLayout.LayoutParams(-1, -2)); root.addView(apiKey, LinearLayout.LayoutParams(-1, -2)); root.addView(pick); root.addView(analyze); root.addView(result)
        setContentView(root)

        pick.setOnClickListener {
            startActivityForResult(Intent(Intent.ACTION_OPEN_DOCUMENT).apply { type = "image/*"; addCategory(Intent.CATEGORY_OPENABLE) }, 100)
        }
        analyze.setOnClickListener { analyzeImage() }
        pick.setOnClickListener {
            startActivityForResult(Intent(Intent.ACTION_OPEN_DOCUMENT).apply { type = "image/*"; addCategory(Intent.CATEGORY_OPENABLE; addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION) }, 100)
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == 100 && resultCode == RESULT_OK) {
            imageUri = data?.data
            result.text = if (imageUri != null) "✅ تم اختيار الصورة. أدخل رابط الخادم ثم اضغط تحليل." else "لم يتم اختيار صورة."
            (findButton("🔎 تحليل الشارت"))?.isEnabled = imageUri != null
        }
    }

    private fun findButton(text: String): Button? {
        val content = window.decorView.findViewById<android.view.ViewGroup>(android.R.id.content)
        fun walk(v: android.view.View): Button? {
            if (v is Button && v.text.toString() == text) return v
            if (v is android.view.ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))?.let { return it }
            return null
        }
        return walk(content)
    }

    private fun analyzeImage() {
        val uri = imageUri ?: return
        val base = apiUrl.text.toString().trim().trimEnd('/')
        val key = apiKey.text.toString().trim()
        if (base.isBlank()) { result.text = "❌ أدخل رابط خادم Pocket OTC AI Analyzer."; return }
        result.text = "⏳ جارٍ رفع الصورة وتحليلها..."
        Thread {
            try {
                val bytes = contentResolver.openInputStream(uri)?.use { it.readBytes() } ?: throw IOException("تعذر قراءة الصورة")
                val body = MultipartBody.Builder().setType(MultipartBody.FORM)
                    .addFormDataPart("file", "chart.jpg", bytes.toRequestBody("image/jpeg".toMediaType()))
                    .build()
                val reqBuilder = Request.Builder().url("$base/api/analyze-image").post(body)
                if (key.isNotBlank()) reqBuilder.addHeader("X-OpenRouter-Key", key)
                client.newCall(reqBuilder.build()).execute().use { response ->
                    val text = response.body?.string() ?: ""
                    if (!response.isSuccessful) throw IOException("HTTP ${response.code}: $text")
                    runOnUiThread { result.text = formatJson(text) }
                }
            } catch (e: Exception) { runOnUiThread { result.text = "❌ ${e.message}" } }
        }.start()
    }

    private fun formatJson(raw: String): String {
        return try {
            val o = org.json.JSONObject(raw)
            "الإشارة: ${o.optString("signal", "NO TRADE")}\nالثقة: ${o.optInt("confidence", 0)}%\nالاتجاه: ${o.optString("direction", "NEUTRAL")}\nالأفق: ${o.optInt("duration_minutes", 1)} دقيقة\n\nالسبب:\n${o.optString("reason", "غير متوفر")}\n\nالمخاطر:\n${o.optString("risks", "غير متوفر")}\n\nالمصدر: ${o.optString("source", "VISION")}\n${o.optString("disclaimer", "تحليل فقط — لا يتم تنفيذ أي صفقة.")}"
        } catch (_: Exception) { raw }
    }
}
