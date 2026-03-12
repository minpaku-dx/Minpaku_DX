import { useEffect, useRef, useState, useCallback } from 'react';
import { Platform } from 'react-native';
import * as Notifications from 'expo-notifications';
import type { EventSubscription } from 'expo-modules-core';
import { useRouter } from 'expo-router';
import { api } from '@/lib/api';
import { useAppStore } from '@/lib/store';

// Foreground: suppress system alert, we'll show a toast instead
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: false,
    shouldShowBanner: false,
    shouldShowList: false,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

async function setupAndroidChannel() {
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', {
      name: '通知',
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
    });
  }
}

export function useNotifications() {
  const [permissionGranted, setPermissionGranted] = useState(false);
  const router = useRouter();
  const showToast = useAppStore((s) => s.showToast);
  const fcmToken = useAppStore((s) => s.fcmToken);
  const setFcmToken = useAppStore((s) => s.setFcmToken);
  const responseListener = useRef<EventSubscription>(undefined);
  const foregroundListener = useRef<EventSubscription>(undefined);

  const requestPermission = useCallback(async () => {
    try {
      await setupAndroidChannel();

      const { status: existingStatus } = await Notifications.getPermissionsAsync();
      let finalStatus = existingStatus;

      if (existingStatus !== 'granted') {
        const { status } = await Notifications.requestPermissionsAsync();
        finalStatus = status;
      }

      if (finalStatus !== 'granted') {
        setPermissionGranted(false);
        return;
      }

      setPermissionGranted(true);

      // Get push token
      const tokenData = await Notifications.getExpoPushTokenAsync();
      const token = tokenData.data;

      if (token && token !== fcmToken) {
        setFcmToken(token);
        await api.registerDevice(token, Platform.OS);
      }
    } catch (err) {
      console.warn('Push notification setup failed:', err);
    }
  }, [fcmToken, setFcmToken]);

  const unregister = useCallback(async () => {
    if (fcmToken) {
      try {
        await api.unregisterDevice(fcmToken);
      } catch {
        // Best effort
      }
      setFcmToken(null);
    }
  }, [fcmToken, setFcmToken]);

  useEffect(() => {
    // Foreground notification → show toast
    foregroundListener.current = Notifications.addNotificationReceivedListener(
      (notification) => {
        const body = notification.request.content.body;
        if (body) {
          showToast(body, 'info');
        }
      },
    );

    // Tap notification → navigate to message
    responseListener.current = Notifications.addNotificationResponseReceivedListener(
      (response) => {
        const data = response.notification.request.content.data;
        if (data?.messageId) {
          router.push(`/messages/${data.messageId}`);
        }
      },
    );

    return () => {
      foregroundListener.current?.remove();
      responseListener.current?.remove();
    };
  }, []);

  return { permissionGranted, requestPermission, unregister };
}
