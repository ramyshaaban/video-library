/**
 * Quick token extraction script
 * Copy and paste this into React Native Debugger console
 * 
 * Make sure you're logged into the StayCurrentMD app first!
 */

(async function extractToken() {
  try {
    // Import AsyncStorage (should be available in React Native context)
    const AsyncStorage = require('@react-native-async-storage/async-storage').default;
    
    console.log('🔍 Extracting token from AsyncStorage...\n');
    
    // Get USER_TOKEN
    const userToken = await AsyncStorage.getItem('USER_TOKEN');
    
    if (userToken) {
      console.log('✅ USER TOKEN FOUND!');
      console.log('📋 Token:', userToken);
      console.log('📏 Length:', userToken.length);
      console.log('🔤 Preview:', userToken.substring(0, 50) + '...\n');
      
      // Also check for other tokens
      const guestToken = await AsyncStorage.getItem('GUEST_TOKEN');
      const tempToken = await AsyncStorage.getItem('TEMP_USER_TOKEN');
      
      console.log('📊 All tokens found:');
      if (userToken) console.log('  - USER_TOKEN: ✅');
      if (guestToken) console.log('  - GUEST_TOKEN: ✅');
      if (tempToken) console.log('  - TEMP_USER_TOKEN: ✅');
      
      console.log('\n💾 Next steps:');
      console.log('1. Copy the USER_TOKEN above');
      console.log('2. Run: echo "TOKEN_HERE" > ~/lab/designer/content_transcriptions/user_token.txt');
      console.log('3. Then run: python3 fetch_all_video_metadata.py');
      
      return userToken;
    } else {
      console.log('❌ No USER_TOKEN found');
      console.log('⚠️  Make sure you are logged into the app!');
      
      // Show all keys to help debug
      const allKeys = await AsyncStorage.getAllKeys();
      console.log('\n📋 All AsyncStorage keys:', allKeys);
      
      const tokenKeys = allKeys.filter(k => k.includes('TOKEN') || k.includes('token'));
      if (tokenKeys.length > 0) {
        console.log('🎫 Token-related keys found:', tokenKeys);
        const tokenValues = await AsyncStorage.multiGet(tokenKeys);
        console.log('📦 Token values:', tokenValues);
      }
      
      return null;
    }
  } catch (error) {
    console.error('❌ Error:', error);
    console.log('\n💡 Tips:');
    console.log('- Make sure React Native Debugger is connected');
    console.log('- Make sure you are logged into the app');
    console.log('- Try using Method 2 (add temporary code to app)');
    return null;
  }
})();

