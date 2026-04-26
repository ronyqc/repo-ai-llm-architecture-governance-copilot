import type { Configuration } from "@azure/msal-browser";
import { LogLevel } from "@azure/msal-browser";
import { env } from "../config/env";

export const msalConfig: Configuration = {
  auth: {
    clientId: env.entraClientId,
    authority: `https://login.microsoftonline.com/${env.entraTenantId}`,
    redirectUri: env.entraRedirectUri,
  },
  cache: {
    cacheLocation: "sessionStorage",
  },
  system: {
    loggerOptions: {
      loggerCallback: (_level, message, containsPii) => {
        if (!containsPii) {
          console.log(message);
        }
      },
      logLevel: LogLevel.Info,
    },
  },
};

export const popupRedirectUri = env.entraPopupRedirectUri;

export const loginRequest = {
  scopes: ["openid", "profile", "email"],
};

export const tokenRequest = {
  scopes: [env.apiScope],
};
