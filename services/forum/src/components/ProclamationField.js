import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { Button, Flex, TextField } from "@radix-ui/themes";
import { postCommand } from "../api";
export function ProclamationField() {
    const [text, setText] = useState("");
    const [busy, setBusy] = useState(false);
    const [err, setErr] = useState(null);
    const submit = async () => {
        if (!text.trim())
            return;
        setBusy(true);
        setErr(null);
        try {
            await postCommand({ kind: "IssueProclamation", text: text.trim() });
            setText("");
        }
        catch (e) {
            setErr(e instanceof Error ? e.message : "failed");
        }
        finally {
            setBusy(false);
        }
    };
    return (_jsxs(Flex, { gap: "2", align: "center", children: [_jsx(TextField.Root, { size: "3", placeholder: "Proclaim a direction\u2026 (e.g. 'users can listen to music, see lyrics scroll, jam together')", value: text, onChange: (e) => setText(e.target.value), onKeyDown: (e) => e.key === "Enter" && !e.shiftKey && submit(), className: "flex-1" }), _jsx(Button, { size: "3", onClick: submit, disabled: busy || !text.trim(), children: "Proclaim" }), err && _jsx("span", { className: "text-red-400 text-sm", children: err })] }));
}
