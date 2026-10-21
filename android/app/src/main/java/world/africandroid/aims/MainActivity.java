package world.africandroid.aims;
import android.app.Activity;
import android.os.Bundle;
import android.content.Intent;
import android.net.Uri;
public class MainActivity extends Activity {
 @Override public void onCreate(Bundle state) {
  super.onCreate(state);
  // Browser-owned authentication and downloads avoid unsafe embedded WebView bridges.
  startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse("https://identity.africandroid.world/")));
  finish();
 }
}
