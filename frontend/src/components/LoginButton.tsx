import { useState } from "react";
import { useAuth } from "../auth/useAuth";

export function LoginButton() {
  const { account, accessToken, authError, isLoadingAuth, signIn, signOut } =
    useAuth();
  const [isBusy, setIsBusy] = useState(false);

  const handleLogin = async () => {
    try {
      setIsBusy(true);
      await signIn();
    } finally {
      setIsBusy(false);
    }
  };

  const handleLogout = async () => {
    try {
      setIsBusy(true);
      await signOut();
    } finally {
      setIsBusy(false);
    }
  };

  const isDisabled = isBusy || isLoadingAuth;

  if (!account) {
    return (
      <div>
        <button disabled={isDisabled} onClick={() => void handleLogin()}>
          {isDisabled ? "Abriendo Microsoft..." : "Iniciar sesion"}
        </button>
        {authError && <small>{authError}</small>}
      </div>
    );
  }

  return (
    <div>
      <div>{account.username}</div>
      {accessToken && (
        <div
          style={{
            display: "inline-block",
            marginTop: "6px",
            marginBottom: "8px",
            padding: "4px 8px",
            borderRadius: "999px",
            backgroundColor: "#dcfce7",
            color: "#166534",
            fontSize: "12px",
            fontWeight: 600,
          }}
        >
          Conectado
        </div>
      )}
      {authError && <small>{authError}</small>}
      <button disabled={isDisabled} onClick={() => void handleLogout()}>
        {isDisabled ? "Cerrando..." : "Cerrar sesion"}
      </button>
    </div>
  );
}
