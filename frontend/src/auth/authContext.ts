import { createContext } from "react";
import type { AccountInfo } from "@azure/msal-browser";

export type AuthContextValue = {
  account: AccountInfo | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoadingAuth: boolean;
  authError: string | null;
  roles: string[];
  scopes: string[];
  isAdmin: boolean;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
  refreshAccessToken: () => Promise<string | null>;
};

export const AuthContext = createContext<AuthContextValue | undefined>(
  undefined
);
