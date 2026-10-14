import { getApp, getApps, initializeApp, type FirebaseOptions } from "firebase/app";
import { getAuth } from "firebase/auth";

const config: FirebaseOptions = JSON.parse(process.env.NEXT_PUBLIC_FIREBASE_CONFIG || "{}");

export const app = getApps().length ? getApp() : initializeApp(config);
export const auth = getAuth(app);
