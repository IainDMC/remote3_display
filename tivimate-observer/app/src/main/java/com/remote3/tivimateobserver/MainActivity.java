package com.remote3.tivimateobserver;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.provider.Settings;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public final class MainActivity extends Activity {
    static final String PREFS = "observer";
    static final String PREF_HA_URL = "ha_url";
    static final String PREF_WEBHOOK_ID = "webhook_id";

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER_HORIZONTAL);
        root.setPadding(72, 48, 72, 48);

        TextView heading = new TextView(this);
        heading.setText("TiviMate Observer");
        heading.setTextSize(30);
        root.addView(heading, matchWrap());

        TextView version = new TextView(this);
        version.setText("Version " + BuildConfig.VERSION_NAME);
        version.setTextSize(14);
        root.addView(version, matchWrap());

        TextView help = new TextView(this);
        help.setText("Enter the local Home Assistant address and private webhook ID, save, then enable TiviMate Observer under Accessibility.");
        help.setTextSize(18);
        help.setPadding(0, 20, 0, 24);
        root.addView(help, matchWrap());

        EditText haUrl = new EditText(this);
        haUrl.setHint("Home Assistant URL, e.g. http://192.168.10.10:8123");
        haUrl.setSingleLine(true);
        haUrl.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        haUrl.setText(prefs.getString(PREF_HA_URL, ""));
        root.addView(haUrl, matchWrap());

        EditText webhook = new EditText(this);
        webhook.setHint("Private webhook ID");
        webhook.setSingleLine(true);
        webhook.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD);
        webhook.setText(prefs.getString(PREF_WEBHOOK_ID, ""));
        root.addView(webhook, matchWrap());

        Button save = new Button(this);
        save.setText("Save settings");
        save.setOnClickListener(v -> {
            String url = trimSlash(haUrl.getText().toString().trim());
            String id = webhook.getText().toString().trim();
            if (!(url.startsWith("http://") || url.startsWith("https://")) || id.isEmpty()) {
                Toast.makeText(this, "Enter a valid URL and webhook ID", Toast.LENGTH_LONG).show();
                return;
            }
            prefs.edit().putString(PREF_HA_URL, url).putString(PREF_WEBHOOK_ID, id).apply();
            Toast.makeText(this, "Saved", Toast.LENGTH_SHORT).show();
        });
        root.addView(save, matchWrap());

        Button accessibility = new Button(this);
        accessibility.setText("Open accessibility settings");
        accessibility.setOnClickListener(v -> startActivity(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)));
        root.addView(accessibility, matchWrap());

        setContentView(root);
    }

    private static LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        );
    }

    private static String trimSlash(String value) {
        while (value.endsWith("/")) value = value.substring(0, value.length() - 1);
        return value;
    }
}
