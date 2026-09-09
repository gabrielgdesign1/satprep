"use client";

import { supabaseBrowser } from "@/lib/supabase-browser";

export default function SignOut() {
  return (
    <button
      onClick={async () => {
        await supabaseBrowser().auth.signOut();
        location.href = "/login";
      }}
      className="rounded-full border-2 border-line bg-surface px-4 py-2 text-sm font-semibold shadow-flat-sm transition-transform hover:-translate-y-0.5 active:translate-y-0 active:shadow-none"
    >
      Sair
    </button>
  );
}
