import { Link } from "expo-router";
import { Text, View } from "react-native";

export default function IndexScreen() {
  return (
    <View
      style={{
        flex: 1,
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
        backgroundColor: "#f7f9fb"
      }}
      testID="mobile-shell"
    >
      <Text style={{ fontSize: 20, fontWeight: "600", color: "#162033" }}>TrueCare</Text>
      <Text style={{ marginTop: 8, color: "#526071", textAlign: "center" }}>
        Nearby car care marketplace
      </Text>
      <Link href="/(consumer)/home" style={{ marginTop: 20, color: "#0f766e", fontWeight: "700" }}>
        Open app
      </Link>
    </View>
  );
}
