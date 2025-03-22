package com.example.testsensors2.presentation

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Bundle
import android.provider.Settings
import android.util.Log
import android.view.WindowManager
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
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
import androidx.wear.ambient.AmbientLifecycleObserver
import androidx.wear.ambient.AmbientModeSupport
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

class MainActivity : FragmentActivity(), AmbientModeSupport.AmbientCallbackProvider {
    private lateinit var heartRateTextView: TextView
    private lateinit var statusTextView: TextView
    private lateinit var healthServicesClient: HealthServicesClient
    private var measuring = false

    private lateinit var sensorManager: SensorManager
    private var skinTempSensor: Sensor? = null
    private var gsrSensor: Sensor? = null
    private lateinit var skinTempTextView: TextView
    private lateinit var gsrTextView: TextView

    private lateinit var ambientController: AmbientModeSupport.AmbientController

    // Backend Server IP Address
    private val SERVER_URL = "http://192.168.0.162:5000/api/heartrate"
    // String representing the device ID
    private lateinit var deviceId: String

    // Timestamp formatter
    private val timestampFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS", Locale.UK)

    // Callback for heart rate data
    private val measureCallback = object : MeasureCallback {
        override fun onAvailabilityChanged(
            dataType: DeltaDataType<*, *>,
            availability: Availability
        ) {
            // Not handling availability changes for now
        }

        // When data is received from the sensors
        override fun onDataReceived(data: DataPointContainer) {
            // Process heart rate data points
            val heartRateSamples = data.getData(DataType.HEART_RATE_BPM)
            heartRateSamples.firstOrNull()?.let { sample ->
                if (sample is SampleDataPoint<Double>) {
                    val heartRate = sample.value.toInt()
                    // Set the heart rate value in the TextView
                    heartRateTextView.text = "$heartRate"

                    // Send heart rate to backend server
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

    // Sensor event listener
    private val sensorEventListener = object : SensorEventListener {
        override fun onSensorChanged(event: SensorEvent) {
            when (event.sensor) {
                skinTempSensor -> {
                    val skinTemp = event.values[0]
                    Log.d("SkinTempSensor", "Skin temperature: $skinTemp")
                    runOnUiThread {
                        skinTempTextView.text = String.format("%.1f°C", skinTemp)
                    }

                    //sendHealthDataToServer("skin_temperature", skinTemp.toInt())
                }
                gsrSensor -> {
                    val gsr = event.values[0]
                    Log.d("GSRSensor", "GSR: $gsr")
                    runOnUiThread {
                        gsrTextView.text = String.format("%.0f kΩ", gsr)
                    }

                    //sendHealthDataToServer("gsr", gsr.toInt())
                }
            }
        }

        override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {
            // Not handling accuracy changes
        }
    }

    private fun initializeSensors() {
        sensorManager = getSystemService(Context.SENSOR_SERVICE) as SensorManager

        // Get skin temperature sensor
        skinTempSensor = sensorManager.getDefaultSensor(Sensor.TYPE_TEMPERATURE)
        if (skinTempSensor == null) {
            // Try custom sensor types if standard ones aren't available
            val deviceSensors = sensorManager.getSensorList(Sensor.TYPE_ALL)
            for (sensor in deviceSensors) {
                if (sensor.name.contains("Skin", ignoreCase = true) &&
                    sensor.name.contains("temp", ignoreCase = true)) {
                    skinTempSensor = sensor
                    Log.d("SkinTempSensor", "Found skin temperature sensor: ${sensor.name}")
                    break
                }
            }
        }

        // Get GSR sensor
        val deviceSensors = sensorManager.getSensorList(Sensor.TYPE_ALL)
        for (sensor in deviceSensors) {
            if (sensor.name.contains("Galvanic", ignoreCase = true)) {
                gsrSensor = sensor
                Log.d("GSRSensor", "Found GSR sensor: ${sensor.name}")
                break
            }
        }

        // Register listeners for the sensors
        if (skinTempSensor != null) {
            sensorManager.registerListener(
                sensorEventListener,
                skinTempSensor,
                SensorManager.SENSOR_DELAY_NORMAL
            )
            skinTempTextView.text = "Waiting..."
        } else {
            skinTempTextView.text = "No sensor"
            Log.d("SkinTempSensor", "Skin temperature sensor not found")
        }

        if (gsrSensor != null) {
            sensorManager.registerListener(
                sensorEventListener,
                gsrSensor,
                SensorManager.SENSOR_DELAY_NORMAL
            )
            gsrTextView.text = "Waiting..."
        } else {
            gsrTextView.text = "No sensor"
            Log.d("GSRSensor", "GSR sensor not found")
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Setup ambient mode
        ambientController = AmbientModeSupport.attach(this)

        // Keep the screen on regardless of ambient mode
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        // Initialize views
        heartRateTextView = findViewById(R.id.heartRateTextView)
        statusTextView = findViewById(R.id.statusTextView)
        skinTempTextView = findViewById(R.id.skinTempTextView)
        gsrTextView = findViewById(R.id.gsrTextView)


        // Get unique device ID for data identification
        deviceId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID)

        // Initialize Health Services
        healthServicesClient = HealthServices.getClient(this)

        sensorManager = getSystemService(Context.SENSOR_SERVICE) as SensorManager

        initializeSensors()

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
        sensorManager.unregisterListener(sensorEventListener)

        // Stop measuring when app is in background
        if (measuring) {
            lifecycleScope.launch {
                try {
                    healthServicesClient.measureClient.unregisterMeasureCallback(
                        DataType.HEART_RATE_BPM,
                        callback = measureCallback
                    )
                    measuring = false
                    statusTextView.text = "Monitoring stopped"
                } catch (e: Exception) {
                    // Handle exception
                }
            }
        }
        // Unregister sensor listeners
        sensorManager.unregisterListener(sensorEventListener)
    }

    override fun onResume() {
        super.onResume()
        // Resume measuring when app comes to foreground
        if (!measuring) {
            checkPermissionAndStartMonitoring()
        }

        if (skinTempSensor != null) {
            sensorManager.registerListener(
                sensorEventListener,
                skinTempSensor,
                SensorManager.SENSOR_DELAY_NORMAL
            )
        }
        if (gsrSensor != null) {
            sensorManager.registerListener(
                sensorEventListener,
                gsrSensor,
                SensorManager.SENSOR_DELAY_NORMAL
            )
        }
    }

    private inner class MyAmbientCallback : AmbientModeSupport.AmbientCallback() {
        override fun onEnterAmbient(ambientDetails: Bundle?) {
            super.onEnterAmbient(ambientDetails)
            // Keep tracking even in ambient mode
            if (!measuring) {
                startHeartRateMonitoring()
            }
        }

        override fun onExitAmbient() {
            super.onExitAmbient()
            // Already in interactive mode
        }

        override fun onUpdateAmbient() {
            super.onUpdateAmbient()
        }
    }

    override fun getAmbientCallback(): AmbientModeSupport.AmbientCallback {
        return MyAmbientCallback()
    }


}