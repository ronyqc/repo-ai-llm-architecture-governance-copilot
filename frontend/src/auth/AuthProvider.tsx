import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useMsal } from "@azure/msal-react";
import type { AccountInfo } from "@azure/msal-browser";
import {
  getAccessToken,
  signIn as signInWithMsal,
  signOut as signOutWithMsal,
} from "./authService";
import { AuthContext, type AuthContextValue } from "./authContext";
import { getAccessTokenClaims } from "./tokenClaims";
import { setStoredAccessToken } from "./tokenStore";

type AuthProviderProps = {
  children: ReactNode;
};

export function AuthProvider({ children }: AuthProviderProps) {
  const { instance, accounts } = useMsal();
  const [account, setAccount] = useState<AccountInfo | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoadingAuth, setIsLoadingAuth] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    const resolvedAccount = instance.getActiveAccount() ?? accounts[0] ?? null;
    if (resolvedAccount) {
      instance.setActiveAccount(resolvedAccount);
    }

    setAccount(resolvedAccount);
  }, [accounts, instance]);

  useEffect(() => {
    const syncToken = async () => {
      if (!account) {
        setStoredAccessToken(null);
        setAccessToken(null);
        setAuthError(null);
        setIsLoadingAuth(false);
        return;
      }

      setIsLoadingAuth(true);
      setAuthError(null);

      try {
        instance.setActiveAccount(account);
        const token = await getAccessToken(instance, account);
        setStoredAccessToken(token);
        setAccessToken(token);
      } catch (error) {
        setStoredAccessToken(null);
        setAccessToken(null);
        setAuthError(
          error instanceof Error
            ? error.message
            : "No se pudo cargar el token de acceso."
        );
      } finally {
        setIsLoadingAuth(false);
      }
    };

    void syncToken();
  }, [account, instance]);

  const handleSignIn = useCallback(async () => {
    setIsLoadingAuth(true);
    setAuthError(null);

    try {
      const loggedAccount = await signInWithMsal(instance);

      if (!loggedAccount) {
        setStoredAccessToken(null);
        setAccessToken(null);
        setAccount(null);
        return;
      }

      instance.setActiveAccount(loggedAccount);
      setAccount(loggedAccount);

      const token = await getAccessToken(instance, loggedAccount);
      setStoredAccessToken(token);
      setAccessToken(token);
    } catch (error) {
      setStoredAccessToken(null);
      setAccessToken(null);
      setAuthError(
        error instanceof Error ? error.message : "Error de autenticacion."
      );
      throw error;
    } finally {
      setIsLoadingAuth(false);
    }
  }, [instance]);

  const handleSignOut = useCallback(async () => {
    setIsLoadingAuth(true);
    setAuthError(null);

    try {
      await signOutWithMsal(instance);
      setStoredAccessToken(null);
      setAccessToken(null);
      setAccount(null);
    } catch (error) {
      setAuthError(
        error instanceof Error ? error.message : "Error al cerrar sesion."
      );
      throw error;
    } finally {
      setIsLoadingAuth(false);
    }
  }, [instance]);

  const refreshAccessToken = useCallback(async (): Promise<string | null> => {
    const activeAccount = instance.getActiveAccount() ?? account;

    if (!activeAccount) {
      setStoredAccessToken(null);
      setAccessToken(null);
      return null;
    }

    setIsLoadingAuth(true);
    setAuthError(null);

    try {
      instance.setActiveAccount(activeAccount);
      const token = await getAccessToken(instance, activeAccount);
      setStoredAccessToken(token);
      setAccessToken(token);
      setAccount(activeAccount);
      return token;
    } catch (error) {
      setStoredAccessToken(null);
      setAccessToken(null);
      setAuthError(
        error instanceof Error
          ? error.message
          : "No se pudo actualizar el token de acceso."
      );
      return null;
    } finally {
      setIsLoadingAuth(false);
    }
  }, [account, instance]);

  const value = useMemo<AuthContextValue>(
    () => {
      const claims = getAccessTokenClaims(accessToken);

      return {
        account,
        accessToken,
        isAuthenticated: Boolean(account),
        isLoadingAuth,
        authError,
        roles: claims.roles,
        scopes: claims.scopes,
        isAdmin: claims.isAdmin,
        signIn: handleSignIn,
        signOut: handleSignOut,
        refreshAccessToken,
      };
    },
    [
      account,
      accessToken,
      isLoadingAuth,
      authError,
      handleSignIn,
      handleSignOut,
      refreshAccessToken,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
