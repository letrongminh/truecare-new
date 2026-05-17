import { useState } from "react";
import { TextInput } from "react-native";
import { StateScaffold } from "../../components/StateScaffold";
import { signup } from "../../lib/auth-store";

export default function SignupScreen() {
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [state, setState] = useState<"ready" | "loading" | "error">("ready");

  async function submit() {
    setState("loading");
    try {
      await signup(identifier, password, "TrueCare user");
      setState("ready");
    } catch {
      setState("error");
    }
  }

  return (
    <StateScaffold testIDPrefix="auth-signup" title="Dang ky TrueCare" subtitle="Tao tai khoan bang email hoac so dien thoai." state={state} primaryAction="Tao tai khoan">
      <TextInput testID="auth-signup-identifier" placeholder="Email hoac so dien thoai" value={identifier} onChangeText={setIdentifier} style={{ minHeight: 48, borderWidth: 1, borderColor: "#d0d5dd", borderRadius: 8, paddingHorizontal: 12 }} />
      <TextInput testID="auth-signup-password" placeholder="Mat khau" secureTextEntry value={password} onChangeText={setPassword} onSubmitEditing={submit} style={{ minHeight: 48, borderWidth: 1, borderColor: "#d0d5dd", borderRadius: 8, paddingHorizontal: 12 }} />
    </StateScaffold>
  );
}
