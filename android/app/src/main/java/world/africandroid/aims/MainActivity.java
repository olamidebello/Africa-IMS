package world.africandroid.aims;
import android.app.Activity;
import android.os.Bundle;
import android.content.Intent;
import android.net.Uri;
import android.graphics.Bitmap;
import android.webkit.*;
import android.widget.*;
import android.view.View;
import android.content.ActivityNotFoundException;
public class MainActivity extends Activity {
 private WebView web; private TextView status; private ValueCallback<Uri[]> chooser;
 private static final String HOME="https://identity.africandroid.world/";
 private boolean internal(Uri u) {return "https".equals(u.getScheme())&&"identity.africandroid.world".equalsIgnoreCase(u.getHost())&&(u.getPort()==-1||u.getPort()==443)&&u.getUserInfo()==null&&!u.getPath().startsWith("/download");}
 private void external(Uri u) {String s=u.getScheme();if(!("https".equals(s)||"mailto".equals(s)||"tel".equals(s)))return;try{startActivity(new Intent(Intent.ACTION_VIEW,u).addCategory(Intent.CATEGORY_BROWSABLE));}catch(ActivityNotFoundException e){status.setText("No app can open this link.");}}
 @Override public void onCreate(Bundle state){super.onCreate(state);
  LinearLayout layout=new LinearLayout(this);layout.setOrientation(LinearLayout.VERTICAL);LinearLayout bar=new LinearLayout(this);
  for(final String action:new String[]{"Home","Reload","Browser"}){Button b=new Button(this);b.setText(action);b.setOnClickListener(new View.OnClickListener(){public void onClick(View v){if(action.equals("Home"))web.loadUrl(HOME);else if(action.equals("Reload"))web.reload();else external(Uri.parse(HOME));}});bar.addView(b,new LinearLayout.LayoutParams(0,-2,1));}
  layout.addView(bar);status=new TextView(this);status.setText("AIMS · Internet required");layout.addView(status);web=new WebView(this);layout.addView(web,new LinearLayout.LayoutParams(-1,0,1));setContentView(layout);
  WebSettings s=web.getSettings();s.setJavaScriptEnabled(true);s.setDomStorageEnabled(true);s.setAllowFileAccess(false);s.setAllowContentAccess(false);s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);s.setGeolocationEnabled(false);s.setSupportMultipleWindows(false);CookieManager.getInstance().setAcceptThirdPartyCookies(web,false);
  web.setWebViewClient(new WebViewClient(){
   @Override public boolean shouldOverrideUrlLoading(WebView v,WebResourceRequest r){if(internal(r.getUrl()))return false;if(r.isForMainFrame())external(r.getUrl());return true;}
   @Override public void onPageStarted(WebView v,String url,Bitmap icon){status.setText("Abeg wait small…");}
   @Override public void onPageFinished(WebView v,String url){status.setText("AIMS · identity.africandroid.world");CookieManager.getInstance().flush();}
   @Override public void onReceivedError(WebView v,WebResourceRequest r,WebResourceError e){if(r.isForMainFrame())status.setText("Connection failed. Check Internet and tap Reload.");}
   @Override public void onReceivedSslError(WebView v,SslErrorHandler h,android.net.http.SslError e){h.cancel();status.setText("Secure connection failed. Website certificate needs repair.");}
  });
  web.setWebChromeClient(new WebChromeClient(){
   @Override public boolean onShowFileChooser(WebView v,ValueCallback<Uri[]> callback,FileChooserParams p){if(chooser!=null)chooser.onReceiveValue(null);chooser=callback;Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT);i.setType("*/*");i.addCategory(Intent.CATEGORY_OPENABLE);i.putExtra(Intent.EXTRA_MIME_TYPES,new String[]{"application/pdf","image/png","image/jpeg"});try{startActivityForResult(i,42);return true;}catch(ActivityNotFoundException e){chooser=null;callback.onReceiveValue(null);status.setText("No document picker available. Use Browser.");return true;}}
  });
  web.setDownloadListener(new DownloadListener(){public void onDownloadStart(String url,String ua,String cd,String mime,long length){status.setText("Opening browser for download. You may need to sign in there.");external(Uri.parse(url));}});
  if(state!=null)web.restoreState(state);else web.loadUrl(HOME);
 }
 @Override protected void onActivityResult(int r,int result,Intent data){super.onActivityResult(r,result,data);if(r==42&&chooser!=null){chooser.onReceiveValue(result==RESULT_OK&&data!=null&&data.getData()!=null?new Uri[]{data.getData()}:null);chooser=null;}}
 @Override protected void onSaveInstanceState(Bundle state){web.saveState(state);super.onSaveInstanceState(state);}
 @Override public void onBackPressed(){if(web.canGoBack())web.goBack();else super.onBackPressed();}
 @Override protected void onDestroy(){if(chooser!=null)chooser.onReceiveValue(null);web.destroy();super.onDestroy();}
}
