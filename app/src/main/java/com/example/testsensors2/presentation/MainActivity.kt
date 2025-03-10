package com.example.testsensors2.presentation

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.provider.Settings
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.health.services.client.HealthServices
import androidx.health.services.client.HealthServicesClient
import androidx.health.services.client.MeasureCallback
import androidx.health.services.client.data.Availability
import androidx.health.services.client.data.DataPointContainer
import androidx.health.services.client.data.DataType
import androidx.health.services.client.data.DataTypeAvailability
import androidx.health.services.client.data.DeltaDataType
import androidx.health.services.client.data.SampleDataPoint
import androidx.health.services.client.getCapabilities
import androidx.health.services.client.unregisterMeasureCallback
import androidx.lifecycle.lifecycleScope
import com.example.testsensors2.R
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : ComponentActivity() {
    private lateinit var heartRateTextView: TextView
    private lateinit var statusTextView: TextView
    private lateinit var healthServicesClient: HealthServicesClient
    private var measuring = false

    // Set your server IP address here
    private val SERVER_URL = "http://192.168.0.162:5000/api/heartrate"
    private lateinit var deviceId: String

    // Timestamp formatter
    private val timestampFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS", Locale.UK)

    // Callback for heart rate data
    private val measureCallback = object : MeasureCallback {
        override fun onAvailabilityChanged(
            dataType: DeltaDataType<*, *>,
            availability: Availability
        ) {
            // Not handling availability changes
        }

        override fun onDataReceived(data: DataPointContainer) {
            // Process heart rate data points
            val heartRateSamples = data.getData(DataType.HEART_RATE_BPM)
            heartRateSamples.firstOrNull()?.let { sample ->
                if (sample is SampleDataPoint<Double>) {
                    val heartRate = sample.value.toInt()
                    heartRateTextView.text = "$heartRate BPM"

                    // Send heart rate to server
                    sendHeartRateToServer(heartRate)
                }
            }
        }
    }

    // Permission request launcher
    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted: Boolean ->
        if (isGranted) {
            startHeartRateMonitoring()
        } else {
            heartRateTextView.text = "Permission required"
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Initialize views
        heartRateTextView = findViewById(R.id.heartRateTextView)
        statusTextView = findViewById(R.id.statusTextView)


        // Get unique device ID for data identification
        deviceId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID)

        // Initialize Health Services
        healthServicesClient = HealthServices.getClient(this)

        // Check and request permissions if needed
        checkPermissionAndStartMonitoring()
    }

    private fun checkPermissionAndStartMonitoring() {
        when {
            ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.BODY_SENSORS
            ) == PackageManager.PERMISSION_GRANTED -> {
                startHeartRateMonitoring()
            }
            else -> {
                requestPermissionLauncher.launch(Manifest.permission.BODY_SENSORS)
            }
        }
    }

    private fun startHeartRateMonitoring() {
        if (measuring) return

        lifecycleScope.launch {
            try {
                val measureClient = healthServicesClient.measureClient

                // Check if heart rate is available
                val capabilities = measureClient.getCapabilities()
                if (!capabilities.supportedDataTypesMeasure.contains(DataType.HEART_RATE_BPM)) {
                    heartRateTextView.text = "Heart rate not supported"
                    return@launch
                }

                // Register callback and start measuring
                measureClient.registerMeasureCallback(DataType.HEART_RATE_BPM, measureCallback)
                heartRateTextView.text = "Measuring..."
                statusTextView.text = "Connected to server"
                measuring = true
            } catch (e: Exception) {
                heartRateTextView.text = "Error: ${e.message}"
                statusTextView.text = "Error starting measurement"
            }
        }
    }

    private fun sendHeartRateToServer(heartRate: Int) {
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                // Create JSON payload
                val jsonPayload = JSONObject().apply {
                    put("device_id", deviceId)
                    put("heart_rate", heartRate)
                    put("timestamp", timestampFormat.format(Date()))
                }

                // Setup HTTP connection
                val url = URL(SERVER_URL)
                val connection = url.openConnection() as HttpURLConnection
                connection.requestMethod = "POST"
                connection.setRequestProperty("Content-Type", "application/json")
                connection.doOutput = true

                // Send data
                val outputStream = connection.outputStream
                val writer = OutputStreamWriter(outputStream)
                writer.write(jsonPayload.toString())
                writer.flush()
                writer.close()

                // Check response
                val responseCode = connection.responseCode
                val success = responseCode in 200..299

                withContext(Dispatchers.Main) {
                    statusTextView.text = if (success) "Data sent successfully" else "Send failed: $responseCode"
                }

                connection.disconnect()
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    statusTextView.text = "Error: ${e.message}"
                }
            }
        }
    }

    override fun onPause() {
        super.onPause()
        // Stop measuring when app is in background
        if (measuring) {
            lifecycleScope.launch {
                try {
                    healthServicesClient.measureClient.unregisterMeasureCallback(
                        DataType.HEART_RATE_BPM,
                        callback = TODO()
                    )
                    measuring = false
                    statusTextView.text = "Monitoring stopped"
                } catch (e: Exception) {
                    // Handle exception
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        // Resume measuring when app comes to foreground
        if (!measuring) {
            checkPermissionAndStartMonitoring()
        }
    }
}