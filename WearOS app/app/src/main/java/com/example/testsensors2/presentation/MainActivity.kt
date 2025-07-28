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
import org.json.JSONArray
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.Timer
import java.util.TimerTask
import java.util.concurrent.ConcurrentLinkedQueue

// Data classes for storing sensor readings
data class HeartRateReading(val value: Int, val timestamp: String)
data class HealthDataReading(val dataType: String, val value: Int, val timestamp: String)
data class MotionDataReading(val dataType: String, val x: Double, val y: Double, val z: Double, val timestamp: String)

class MainActivity : FragmentActivity(), AmbientModeSupport.AmbientCallbackProvider {
    private lateinit var heartRateTextView: TextView
    private lateinit var statusTextView: TextView
    private lateinit var healthServicesClient: HealthServicesClient
    private var measuring = false

    private lateinit var sensorManager: SensorManager
    private var skinTempSensor: Sensor? = null
    private var gsrSensor: Sensor? = null
    private var lightSensor: Sensor? = null
    private var ppgSensor: Sensor? = null
    private var accelerometerSensor: Sensor? = null
    private var gyroscopeSensor: Sensor? = null
    private lateinit var skinTempTextView: TextView
    private lateinit var gsrTextView: TextView
    private lateinit var lightTextView: TextView

    private lateinit var ambientController: AmbientModeSupport.AmbientController

    // Backend Server IP Address
    private val SERVER_URL = "http://192.168.0.98:5000/api"
    private val samplingPeriod = 33_333 //30 Hz
    private val BATCH_SEND_INTERVAL = 10_000L // 10 seconds in milliseconds

    // String representing the device ID
    private lateinit var deviceId: String

    // Timestamp formatter
    private val timestampFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS", Locale.UK)

    // Data storage queues for batching
    private val heartRateQueue = ConcurrentLinkedQueue<HeartRateReading>()
    private val healthDataQueue = ConcurrentLinkedQueue<HealthDataReading>()
    private val motionDataQueue = ConcurrentLinkedQueue<MotionDataReading>()

    // Timer for batch sending
    private var batchSendTimer: Timer? = null

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
                    runOnUiThread {
                        heartRateTextView.text = "$heartRate"
                    }

                    // Add to queue for batch sending
                    val reading = HeartRateReading(heartRate, timestampFormat.format(Date()))
                    heartRateQueue.offer(reading)
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
            val timestamp = timestampFormat.format(Date())

            when (event.sensor) {
                skinTempSensor -> {
                    val skinTemp = event.values[0]
                    Log.d("SkinTempSensor", "Skin temperature: $skinTemp")
                    runOnUiThread {
                        skinTempTextView.text = String.format("%.1f°C", skinTemp)
                    }

                    // Add to queue for batch sending
                    val reading = HealthDataReading("skin_temperature", skinTemp.toInt(), timestamp)
                    healthDataQueue.offer(reading)
                }
                gsrSensor -> {
                    val gsr = event.values[0]
                    Log.d("GSRSensor", "GSR: $gsr")
                    runOnUiThread {
                        gsrTextView.text = String.format("%.0f kΩ", gsr)
                    }

                    // Add to queue for batch sending
                    val reading = HealthDataReading("gsr", gsr.toInt(), timestamp)
                    healthDataQueue.offer(reading)
                }
                lightSensor -> {
                    val light = event.values[0]
                    Log.d("LightSensor", "Light: $light")
                    runOnUiThread {
                        lightTextView.text = String.format("%.0f", light)
                    }

                    // Add to queue for batch sending
                    val reading = HealthDataReading("light", light.toInt(), timestamp)
                    healthDataQueue.offer(reading)
                }

                ppgSensor -> {
                    val ppg = event.values[0]
                    Log.d("PPGSensor", "PPG: $ppg")

                    // Add to queue for batch sending
                    val reading = HealthDataReading("ppg", ppg.toInt(), timestamp)
                    healthDataQueue.offer(reading)
                }

                accelerometerSensor -> {
                    val accX = event.values[0]
                    val accY = event.values[1]
                    val accZ = event.values[2]

                    Log.d("accX", accX.toString())
                    Log.d("accY", accY.toString())
                    Log.d("accZ", accZ.toString())

                    // Add to queue for batch sending
                    val reading = MotionDataReading("accelerometer", accX.toDouble(), accY.toDouble(), accZ.toDouble(), timestamp)
                    motionDataQueue.offer(reading)
                }

                gyroscopeSensor -> {
                    val gyrX = event.values[0]
                    val gyrY = event.values[1]
                    val gyrZ = event.values[2]

                    Log.d("gyrX", gyrX.toString())
                    Log.d("gyrY", gyrY.toString())
                    Log.d("gyrZ", gyrZ.toString())

                    // Add to queue for batch sending
                    val reading = MotionDataReading("gyroscope", gyrX.toDouble(), gyrY.toDouble(), gyrZ.toDouble(), timestamp)
                    motionDataQueue.offer(reading)
                }
            }
        }

        override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {
            // Not handling accuracy changes
        }
    }

    private fun startBatchSendTimer() {
        batchSendTimer?.cancel()
        batchSendTimer = Timer()
        batchSendTimer?.scheduleAtFixedRate(object : TimerTask() {
            override fun run() {
                sendBatchedDataToServer()
            }
        }, BATCH_SEND_INTERVAL, BATCH_SEND_INTERVAL)
    }

    private fun stopBatchSendTimer() {
        batchSendTimer?.cancel()
        batchSendTimer = null
    }

    private fun sendBatchedDataToServer() {
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                // Collect all data from queues
                val heartRateData = mutableListOf<HeartRateReading>()
                val healthData = mutableListOf<HealthDataReading>()
                val motionData = mutableListOf<MotionDataReading>()

                // Drain queues
                while (heartRateQueue.isNotEmpty()) {
                    heartRateQueue.poll()?.let { heartRateData.add(it) }
                }
                while (healthDataQueue.isNotEmpty()) {
                    healthDataQueue.poll()?.let { healthData.add(it) }
                }
                while (motionDataQueue.isNotEmpty()) {
                    motionDataQueue.poll()?.let { motionData.add(it) }
                }

                val totalDataPoints = heartRateData.size + healthData.size + motionData.size

                if (totalDataPoints == 0) {
                    Log.d("BatchSend", "No data to send")
                    return@launch
                }

                Log.d("BatchSend", "Sending batch: HR=${heartRateData.size}, Health=${healthData.size}, Motion=${motionData.size}")

                // Create batch payload
                val batchPayload = JSONObject().apply {
                    put("device_id", deviceId)
                    put("batch_timestamp", timestampFormat.format(Date()))

                    // Heart rate data
                    if (heartRateData.isNotEmpty()) {
                        val heartRateArray = JSONArray()
                        heartRateData.forEach { reading ->
                            val hrObject = JSONObject().apply {
                                put("heart_rate", reading.value)
                                put("timestamp", reading.timestamp)
                            }
                            heartRateArray.put(hrObject)
                        }
                        put("heart_rate_data", heartRateArray)
                    }

                    // Health data (skin temp, GSR, light, PPG)
                    if (healthData.isNotEmpty()) {
                        val healthArray = JSONArray()
                        healthData.forEach { reading ->
                            val healthObject = JSONObject().apply {
                                put("data_type", reading.dataType)
                                put("value", reading.value)
                                put("timestamp", reading.timestamp)
                            }
                            healthArray.put(healthObject)
                        }
                        put("health_data", healthArray)
                    }

                    // Motion data (accelerometer, gyroscope)
                    if (motionData.isNotEmpty()) {
                        val motionArray = JSONArray()
                        motionData.forEach { reading ->
                            val motionObject = JSONObject().apply {
                                put("data_type", reading.dataType)
                                put("x_value", reading.x)
                                put("y_value", reading.y)
                                put("z_value", reading.z)
                                put("timestamp", reading.timestamp)
                            }
                            motionArray.put(motionObject)
                        }
                        put("motion_data", motionArray)
                    }
                }

                // Send batch to server
                val url = URL("$SERVER_URL/batch")
                val connection = url.openConnection() as HttpURLConnection
                connection.requestMethod = "POST"
                connection.setRequestProperty("Content-Type", "application/json")
                connection.doOutput = true
                connection.connectTimeout = 10000 // 10 seconds timeout
                connection.readTimeout = 10000

                // Send data
                val outputStream = connection.outputStream
                val writer = OutputStreamWriter(outputStream)
                writer.write(batchPayload.toString())
                writer.flush()
                writer.close()

                // Check response
                val responseCode = connection.responseCode
                val success = responseCode in 200..299

                withContext(Dispatchers.Main) {
                    statusTextView.text = if (success) {
                        "Batch sent: $totalDataPoints points"
                    } else {
                        "Batch failed: $responseCode"
                    }
                }

                connection.disconnect()

                Log.d("BatchSend", "Batch sent successfully. Response: $responseCode")

            } catch (e: Exception) {
                Log.e("BatchSend", "Error sending batch: ${e.message}", e)
                withContext(Dispatchers.Main) {
                    statusTextView.text = "Batch error: ${e.message}"
                }
            }
        }
    }

    private fun initializeSensors() {
        sensorManager = getSystemService(SENSOR_SERVICE) as SensorManager

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

        // Get GSR, light sensor, PPG Sensor, Accelerometer and Gyroscope
        val deviceSensors = sensorManager.getSensorList(Sensor.TYPE_ALL)
        Log.d("Sensors", "Found ${deviceSensors.size} sensors")

        for (sensor in deviceSensors) {
            Log.d("Sensor", "SensorName: ${sensor.name}")
            if (sensor.name.contains("Galvanic", ignoreCase = true) && gsrSensor == null) {
                gsrSensor = sensor
                Log.d("GSRSensor", "Found GSR sensor: ${sensor.name}")
            }

            if (sensor.name.contains("light", ignoreCase = true) && lightSensor == null) {
                lightSensor = sensor
                Log.d("LightSensor", "Found Light sensor: ${sensor.name}")
            }

            if (sensor.name.contains("PPG Controller", ignoreCase = true) && ppgSensor == null) {
                ppgSensor = sensor
                Log.d("PPGSensor", "Found PPG sensor: ${sensor.name}")
            }

            if (sensor.name.contains("Accelerometer", ignoreCase = true) && accelerometerSensor == null) {
                accelerometerSensor = sensor
                Log.d("AccelerometerSensor", "Found Accelerometer: ${sensor.name}")
            }

            if (sensor.name.contains("Gyroscope", ignoreCase = true) && gyroscopeSensor == null) {
                gyroscopeSensor = sensor
                Log.d("GyroscopeSensor", "Found Gyroscope: ${sensor.name}")
            }

            if(gsrSensor != null && lightSensor != null && ppgSensor != null && accelerometerSensor != null && gyroscopeSensor != null) break
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

        if (lightSensor != null) {
            sensorManager.registerListener(
                sensorEventListener,
                lightSensor,
                SensorManager.SENSOR_DELAY_NORMAL
            )
            lightTextView.text = "Waiting..."
        } else {
            lightTextView.text = "No sensor"
            Log.d("LightSensor", "Light sensor not found")
        }

        if (ppgSensor != null) {
            sensorManager.registerListener(
                sensorEventListener,
                ppgSensor,
                SensorManager.SENSOR_DELAY_NORMAL
            )
        } else {
            Log.d("PPGSensor", "PPG sensor not found")
        }

        if (accelerometerSensor != null) {
            sensorManager.registerListener(
                sensorEventListener,
                accelerometerSensor,
                samplingPeriod
            )
        } else {
            Log.d("AccelerometerSensor", "Accelerometer not found")
        }

        if (gyroscopeSensor != null) {
            sensorManager.registerListener(
                sensorEventListener,
                gyroscopeSensor,
                samplingPeriod
            )
        } else {
            Log.d("GyroscopeSensor", "Gyroscope not found")
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
        lightTextView = findViewById(R.id.lightTextView)

        // Get unique device ID for data identification
        deviceId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID)

        // Initialize Health Services
        healthServicesClient = HealthServices.getClient(this)

        sensorManager = getSystemService(SENSOR_SERVICE) as SensorManager

        initializeSensors()
        startBatchSendTimer() // Start the batch sending timer

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
                statusTextView.text = "Batching data..."
                measuring = true
            } catch (e: Exception) {
                heartRateTextView.text = "Error: ${e.message}"
                statusTextView.text = "Error starting measurement"
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

        // Stop the batch timer when app is paused
        stopBatchSendTimer()
    }

    override fun onResume() {
        super.onResume()
        // Resume measuring when app comes to foreground
        if (!measuring) {
            checkPermissionAndStartMonitoring()
        }

        // Restart the batch timer
        startBatchSendTimer()

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

        if (lightSensor != null) {
            sensorManager.registerListener(
                sensorEventListener,
                lightSensor,
                SensorManager.SENSOR_DELAY_NORMAL
            )
        }

        if (ppgSensor != null) {
            sensorManager.registerListener(
                sensorEventListener,
                ppgSensor,
                SensorManager.SENSOR_DELAY_NORMAL
            )
        }

        if (accelerometerSensor != null) {
            sensorManager.registerListener(
                sensorEventListener,
                accelerometerSensor,
                samplingPeriod
            )
        }

        if (gyroscopeSensor != null) {
            sensorManager.registerListener(
                sensorEventListener,
                gyroscopeSensor,
                samplingPeriod
            )
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        stopBatchSendTimer()

        // Send any remaining data before destroying
        sendBatchedDataToServer()
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