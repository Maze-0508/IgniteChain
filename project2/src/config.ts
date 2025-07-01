// src/config.ts
import { createConfig } from "@0xsequence/connect";

export const config = createConfig("waas", {
    projectAccessKey: "AQAAAAAAAKZa4vjqL4KT_WWYO_Jhbzua6T4",
    chainIds: [1, 137],
    defaultChainId: 1,
        appName: "Demo",
        waasConfigKey: "eyJwcm9qZWN0SWQiOjQyNTg2LCJycGNTZXJ2ZXIiOiJodHRwczovL3dhYXMuc2VxdWVuY2UuYXBwIn0=",
        google: {
            clientId: "27869525669-c3qu62pkleguurk268jlo78nbm79rrre.apps.googleusercontent.com",
        },
        walletConnect: {
            projectId: "06eb419580cbdacb102da8562f161924",
        },
});
