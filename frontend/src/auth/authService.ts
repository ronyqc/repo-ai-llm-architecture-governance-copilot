import {
  InteractionRequiredAuthError,
  type AccountInfo,
  type IPublicClientApplication,
} from "@azure/msal-browser";
import { loginRequest, popupRedirectUri, tokenRequest } from "./msalConfig";

function getErrorMessage(error: unknown, fallbackMessage: string): string {
  if (error instanceof Error && error.message.trim().length > 0) {
    return `${fallbackMessage} ${error.message}`;
  }

  return fallbackMessage;
}

export async function signIn(msalInstance: IPublicClientApplication) {
  try {
    const response = await msalInstance.loginPopup({
      ...loginRequest,
      redirectUri: popupRedirectUri,
    });
    console.log("response.account:", response.account);
    return response.account;
  } catch (error) {
    throw new Error(
      getErrorMessage(error, "No se pudo iniciar sesion con Microsoft.")
    );
  }
}

export async function signOut(msalInstance: IPublicClientApplication) {
  try {
    const account = msalInstance.getActiveAccount();
    await msalInstance.logoutPopup({
      account: account || undefined,
    });
  } catch (error) {
    throw new Error(
      getErrorMessage(error, "No se pudo cerrar sesion correctamente.")
    );
  }
}

export async function getAccessToken(
  msalInstance: IPublicClientApplication,
  account: AccountInfo
): Promise<string | null> {
  try {
    const response = await msalInstance.acquireTokenSilent({
      ...tokenRequest,
      account,
    });
    return response.accessToken;
  } catch (error) {
    if (error instanceof InteractionRequiredAuthError) {
      try {
        const response = await msalInstance.acquireTokenPopup({
          ...tokenRequest,
          account,
          redirectUri: popupRedirectUri,
        });
        return response.accessToken;
      } catch (popupError) {
        throw new Error(
          getErrorMessage(popupError, "No se pudo obtener el token de acceso.")
        );
      }
    }

    throw new Error(
      getErrorMessage(
        error,
        "No se pudo obtener el token de acceso en modo silencioso."
      )
    );
  }
}
