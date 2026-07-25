package com.remote3.tivimateobserver;

import android.accessibilityservice.AccessibilityService;
import android.content.SharedPreferences;
import android.os.Handler;
import android.os.Looper;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import org.json.JSONObject;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class TiviMateAccessibilityService extends AccessibilityService {
    private static final String PACKAGE = "ar.tvplayer.tv";
    private static final String CHANNEL_ID = PACKAGE + ":id/b7";
    private static final String PROGRAM_ID = PACKAGE + ":id/152";
    private static final String TIME_ID = PACKAGE + ":id/315";

    private final Handler handler = new Handler(Looper.getMainLooper());
    private final ExecutorService network = Executors.newSingleThreadExecutor();
    private String lastPayload = "";

    private final Runnable inspect = this::inspectVisibleUi;

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        if (event.getPackageName() == null || !PACKAGE.contentEquals(event.getPackageName())) return;
        handler.removeCallbacks(inspect);
        handler.postDelayed(inspect, 150);
    }

    @Override
    public void onInterrupt() { }

    @Override
    public void onDestroy() {
        handler.removeCallbacksAndMessages(null);
        network.shutdownNow();
        super.onDestroy();
    }

    private void inspectVisibleUi() {
        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null) return;
        try {
            String channel = firstText(root, CHANNEL_ID);
            if (channel.isEmpty()) return;
            String program = firstText(root, PROGRAM_ID);
            String timeRange = firstText(root, TIME_ID);

            JSONObject json = new JSONObject();
            json.put("channel", channel);
            json.put("program", program);
            json.put("time_range", timeRange);
            json.put("source", "tivimate_observer");
            String payload = json.toString();
            if (payload.equals(lastPayload)) return;
            lastPayload = payload;
            post(payload);
        } catch (Exception ignored) {
            // Accessibility services must never disrupt the TV UI.
        } finally {
            root.recycle();
        }
    }

    private static String firstText(AccessibilityNodeInfo root, String viewId) {
        List<AccessibilityNodeInfo> nodes = root.findAccessibilityNodeInfosByViewId(viewId);
        if (nodes == null) return "";
        try {
            for (AccessibilityNodeInfo node : nodes) {
                CharSequence text = node.getText();
                if (text != null && !text.toString().trim().isEmpty()) return text.toString().trim();
            }
            return "";
        } finally {
            for (AccessibilityNodeInfo node : nodes) node.recycle();
        }
    }

    private void post(String payload) {
        SharedPreferences prefs = getSharedPreferences(MainActivity.PREFS, MODE_PRIVATE);
        String base = prefs.getString(MainActivity.PREF_HA_URL, "");
        String id = prefs.getString(MainActivity.PREF_WEBHOOK_ID, "");
        if (base.isEmpty() || id.isEmpty()) return;
        String endpoint = base + "/api/webhook/" + id;
        network.execute(() -> {
            HttpURLConnection connection = null;
            try {
                connection = (HttpURLConnection) new URL(endpoint).openConnection();
                connection.setRequestMethod("POST");
                connection.setConnectTimeout(3000);
                connection.setReadTimeout(3000);
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                byte[] body = payload.getBytes(StandardCharsets.UTF_8);
                connection.setFixedLengthStreamingMode(body.length);
                try (OutputStream output = connection.getOutputStream()) {
                    output.write(body);
                }
                connection.getResponseCode();
            } catch (Exception ignored) {
                // A later TiviMate content change will retry with fresh data.
                lastPayload = "";
            } finally {
                if (connection != null) connection.disconnect();
            }
        });
    }
}
