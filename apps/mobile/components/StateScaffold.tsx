import { ReactNode } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";

export type StateScaffoldProps = {
  testIDPrefix: string;
  title: string;
  subtitle?: string;
  state?: "ready" | "loading" | "empty" | "error" | "offline" | "forbidden";
  primaryAction?: string;
  secondaryAction?: string;
  children?: ReactNode;
};

const stateCopy = {
  ready: "",
  loading: "Dang tai du lieu",
  empty: "Chua co du lieu",
  error: "Khong tai duoc du lieu",
  offline: "Dang ngoai tuyen",
  forbidden: "Ban khong co quyen truy cap"
};

export function StateScaffold({
  testIDPrefix,
  title,
  subtitle,
  state = "ready",
  primaryAction = "Tiep tuc",
  secondaryAction = "Thu lai",
  children
}: StateScaffoldProps) {
  return (
    <ScrollView
      testID={`${testIDPrefix}-screen`}
      style={{ flex: 1, backgroundColor: "#f6f8fb" }}
      contentContainerStyle={{ padding: 20, gap: 16 }}
    >
      <View style={{ gap: 6 }}>
        <Text testID={`${testIDPrefix}-title`} style={{ color: "#182230", fontSize: 26, fontWeight: "700" }}>
          {title}
        </Text>
        {subtitle ? (
          <Text style={{ color: "#667085", fontSize: 15, lineHeight: 22 }}>
            {subtitle}
          </Text>
        ) : null}
      </View>

      {state !== "ready" ? (
        <View
          testID={`${testIDPrefix}-${state}`}
          style={{ borderColor: "#d0d5dd", borderWidth: 1, borderRadius: 8, padding: 14, backgroundColor: "#ffffff" }}
        >
          <Text style={{ color: "#344054", fontWeight: "600" }}>{stateCopy[state]}</Text>
        </View>
      ) : null}

      <View style={{ gap: 10 }}>{children}</View>

      <View style={{ flexDirection: "row", gap: 10 }}>
        <Pressable
          testID={`${testIDPrefix}-primary`}
          style={{ minHeight: 48, flex: 1, borderRadius: 8, alignItems: "center", justifyContent: "center", backgroundColor: "#0f766e" }}
        >
          <Text style={{ color: "#ffffff", fontWeight: "700" }}>{primaryAction}</Text>
        </Pressable>
        <Pressable
          testID={`${testIDPrefix}-retry`}
          style={{ minHeight: 48, flex: 1, borderRadius: 8, alignItems: "center", justifyContent: "center", borderColor: "#98a2b3", borderWidth: 1 }}
        >
          <Text style={{ color: "#344054", fontWeight: "700" }}>{secondaryAction}</Text>
        </Pressable>
      </View>
    </ScrollView>
  );
}

export function DataRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 12, paddingVertical: 8 }}>
      <Text style={{ color: "#667085" }}>{label}</Text>
      <Text style={{ color: "#182230", fontWeight: "600", flexShrink: 1, textAlign: "right" }}>{value}</Text>
    </View>
  );
}
