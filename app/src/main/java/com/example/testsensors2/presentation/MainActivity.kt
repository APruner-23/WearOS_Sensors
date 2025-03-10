/* While this template provides a good starting point for using Wear Compose, you can always
 * take a look at https://github.com/android/wear-os-samples/tree/main/ComposeStarter to find the
 * most up to date changes to the libraries and their usages.
 */

package com.example.testsensors2.presentation

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
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
import androidx.health.services.client.data.HeartRateAccuracy
import androidx.health.services.client.data.SampleDataPoint
import androidx.health.services.client.getCapabilities
import androidx.health.services.client.unregisterMeasureCallback
import androidx.lifecycle.lifecycleScope
import com.example.testsensors2.R
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    private lateinit var heartRateTextView: TextView
    private lateinit var healthServicesClient: HealthServicesClient
    private var measuring = false

    // Callback for heart rate data
    private val measureCallback = object : MeasureCallback {
        override fun onAvailabilityChanged(
            dataType: DeltaDataType<*, *>,
            availability: Availability
        ) {
//            if (dataType == DataType.HEART_RATE_BPM && availability != DataTypeAvailability.AVAILABLE) {
//                heartRateTextView.text = "Heart rate unavailable"
//
//            }
        }

        override fun onDataReceived(data: DataPointContainer) {
            // Process heart rate data points
            val heartRateSamples = data.getData(DataType.HEART_RATE_BPM)
            heartRateSamples.firstOrNull()?.let { sample ->
                if (sample is SampleDataPoint<Double>) {
                    val heartRate = sample.value.toInt()
                    heartRateTextView.text = "$heartRate BPM"
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
                measuring = true
            } catch (e: Exception) {
                heartRateTextView.text = "Error: ${e.message}"
            }
        }
    }
}