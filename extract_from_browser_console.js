/**
 * Run this in the browser console when the app is loaded
 * This will extract the token from AsyncStorage
 * 
 * Instructions:
 * 1. Open the app in browser (usually http://localhost:8081)
 * 2. Log in to the app
 * 3. Open browser DevTools (F12 or Cmd+Option+I)
 * 4. Go to Console tab
 * 5. Paste and run this script
 */

(async function() {
  try {
    console.log('🔍 Extracting token from AsyncStorage...\n');
    
    // For web, AsyncStorage uses localStorage
    // Check if we can access it through the app's context
    const token = localStorage.getItem('USER_TOKEN') || 
                  localStorage.getItem('@AsyncStorage:USER_TOKEN') ||
                  sessionStorage.getItem('USER_TOKEN');
    
    if (token) {
      console.log('✅ TOKEN FOUND!');
      console.log('📋 Token:', token);
      console.log('📏 Length:', token.length);
      console.log('\n💾 Copy this token and run:');
      console.log(`echo "${token}" > ~/lab/designer/content_transcriptions/user_token.txt`);
      
      // Try to copy to clipboard
      if (navigator.clipboard) {
        navigator.clipboard.writeText(token).then(() => {
          console.log('✅ Token copied to clipboard!');
        });
      }
      
      return token;
    } else {
      console.log('❌ No token found in localStorage');
      console.log('📋 Checking all localStorage keys...');
      
      const allKeys = Object.keys(localStorage);
      console.log('All localStorage keys:', allKeys);
      
      const tokenKeys = allKeys.filter(k => k.includes('TOKEN') || k.includes('token'));
      if (tokenKeys.length > 0) {
        console.log('🎫 Token-related keys found:', tokenKeys);
        tokenKeys.forEach(key => {
          console.log(`${key}:`, localStorage.getItem(key));
        });
      }
      
      console.log('\n💡 The token might be stored differently in web.');
      console.log('Try checking the Network tab for API requests - the token will be in the Authorization header.');
      
      return null;
    }
  } catch (error) {
    console.error('❌ Error:', error);
    console.log('\n💡 Alternative: Check Network tab in DevTools');
    console.log('1. Open Network tab');
    console.log('2. Make any API request (navigate, search, etc.)');
    console.log('3. Look for requests to api.staycurrentmd.com/graphql');
    console.log('4. Check Request Headers > Authorization');
    console.log('5. Copy the Bearer token value');
  }
})();

