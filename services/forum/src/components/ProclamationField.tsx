import { useState } from "react";
import { Button, Flex, TextField } from "@radix-ui/themes";
import { postCommand } from "../api";

export function ProclamationField() {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const submit = async () => {
    if (!text.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      await postCommand({ kind: "IssueProclamation", text: text.trim() });
      setText("");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Flex gap="2" align="center">
      <TextField.Root
        size="3"
        placeholder="Proclaim a direction… (e.g. 'users can listen to music, see lyrics scroll, jam together')"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && submit()}
        className="flex-1"
      />
      <Button size="3" onClick={submit} disabled={busy || !text.trim()}>
        Proclaim
      </Button>
      {err && <span className="text-red-400 text-sm">{err}</span>}
    </Flex>
  );
}
