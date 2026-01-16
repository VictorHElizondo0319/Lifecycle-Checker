'use client';

import { useState, useEffect } from 'react';
import { getAzureStatus, getAzureSubscriptions, setAzureSubscription, AzureStatusResponse, AzureSubscription } from '@/lib/api';

const STORAGE_KEY_STATUS = 'azure_status';
const STORAGE_KEY_SUBSCRIPTIONS = 'azure_subscriptions';

// Helper functions for localStorage
const loadStatusFromStorage = (): AzureStatusResponse | null => {
  if (typeof window === 'undefined') return null;
  try {
    const stored = localStorage.getItem(STORAGE_KEY_STATUS);
    return stored ? JSON.parse(stored) : null;
  } catch {
    return null;
  }
};

const saveStatusToStorage = (status: AzureStatusResponse | null) => {
  if (typeof window === 'undefined') return;
  try {
    if (status) {
      localStorage.setItem(STORAGE_KEY_STATUS, JSON.stringify(status));
    } else {
      localStorage.removeItem(STORAGE_KEY_STATUS);
    }
  } catch (error) {
    console.error('Failed to save status to localStorage:', error);
  }
};

const loadSubscriptionsFromStorage = (): AzureSubscription[] => {
  if (typeof window === 'undefined') return [];
  try {
    const stored = localStorage.getItem(STORAGE_KEY_SUBSCRIPTIONS);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
};

const saveSubscriptionsToStorage = (subscriptions: AzureSubscription[]) => {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY_SUBSCRIPTIONS, JSON.stringify(subscriptions));
  } catch (error) {
    console.error('Failed to save subscriptions to localStorage:', error);
  }
};

export default function AzureStatus() {
  // Initialize from localStorage if available (for Electron persistence)
  const [status, setStatus] = useState<AzureStatusResponse | null>(() => loadStatusFromStorage());
  const [subscriptions, setSubscriptions] = useState<AzureSubscription[]>(() => loadSubscriptionsFromStorage());
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [showSubscriptions, setShowSubscriptions] = useState(false);
  const [selectingSubscription, setSelectingSubscription] = useState(false);

  // Save to localStorage whenever status changes
  useEffect(() => {
    saveStatusToStorage(status);
  }, [status]);

  // Save to localStorage whenever subscriptions change
  useEffect(() => {
    if (subscriptions.length > 0) {
      saveSubscriptionsToStorage(subscriptions);
    }
  }, [subscriptions]);

  const fetchStatus = async () => {
    try {
      setLoading(true);
      const statusData = await getAzureStatus();
      setStatus(statusData);
      
      if (statusData.logged_in) {
        const subsData = await getAzureSubscriptions();
        setSubscriptions(subsData.subscriptions);
      } else {
        // Clear subscriptions if not logged in
        setSubscriptions([]);
      }
    } catch (error) {
      console.error('Failed to fetch Azure status:', error);
      const errorStatus: AzureStatusResponse = {
        success: false,
        logged_in: false,
        error: error instanceof Error ? error.message : 'Failed to fetch Azure status'
      };
      setStatus(errorStatus);
      setSubscriptions([]);
    } finally {
      setLoading(false);
    }
  };

  const refreshStatus = async () => {
    setRefreshing(true);
    await fetchStatus();
    setRefreshing(false);
  };

  const handleChangeSubscription = async () => {
    if (!showSubscriptions) {
      // When opening subscriptions, fetch status if not already loaded
      if (!status) {
        await fetchStatus();
      } else if (status.logged_in && subscriptions.length === 0) {
        // If logged in but subscriptions not loaded, fetch them
        try {
          const subsData = await getAzureSubscriptions();
          setSubscriptions(subsData.subscriptions);
        } catch (error) {
          console.error('Failed to fetch subscriptions:', error);
        }
      }
    }
    setShowSubscriptions(!showSubscriptions);
  };

  const handleSetSubscription = async (subscriptionId: string) => {
    try {
      setSelectingSubscription(true);
      await setAzureSubscription({ subscription_id: subscriptionId });
      await fetchStatus(); // Refresh status after setting subscription
      setShowSubscriptions(false);
    } catch (error) {
      console.error('Failed to set subscription:', error);
      alert(error instanceof Error ? error.message : 'Failed to set subscription');
    } finally {
      setSelectingSubscription(false);
    }
  };

  // Clear stored data (useful for debugging or logout)
  const clearStoredData = () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem(STORAGE_KEY_STATUS);
      localStorage.removeItem(STORAGE_KEY_SUBSCRIPTIONS);
    }
  };

  const isLoggedIn = status?.logged_in ?? false;
  const currentSubscription = status?.subscription;
  const hasNotChecked = status === null;

  if (loading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="flex items-center gap-2">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-purple-600"></div>
          <span className="text-sm text-gray-600">Checking Azure status...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className={`h-3 w-3 rounded-full ${
            hasNotChecked ? 'bg-gray-400' : (isLoggedIn ? 'bg-green-500' : 'bg-red-500')
          }`}></div>
          <h3 className="text-sm font-semibold text-gray-800">Azure Status</h3>
        </div>
        <button
          onClick={refreshStatus}
          disabled={refreshing || loading}
          className="text-xs text-purple-600 hover:text-purple-700 disabled:opacity-50"
          title="Refresh status"
        >
          {refreshing ? '⟳' : '↻'}
        </button>
      </div>

      {hasNotChecked ? (
        <div className="space-y-2">
          <p className="text-xs text-gray-600">
            Click refresh to check Azure login status
          </p>
          <button
            onClick={refreshStatus}
            className="w-full rounded bg-purple-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-purple-700"
          >
            Check Status
          </button>
        </div>
      ) : !isLoggedIn ? (
        <div className="space-y-2">
          <p className="text-xs text-red-600">
            Not logged in to Azure CLI
          </p>
          <p className="text-xs text-gray-500">
            Run <code className="bg-gray-100 px-1 py-0.5 rounded">az login</code> in your terminal
          </p>
          {status?.error && (
            <p className="text-xs text-red-500 mt-1">
              Error: {status.error}
            </p>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {status?.account && (
            <div>
              <p className="text-xs text-gray-600 mb-1">Account</p>
              <p className="text-sm font-medium text-gray-800">
                {status.account.name || status.account.id}
              </p>
            </div>
          )}

          {currentSubscription ? (
            <div>
              <div className="flex items-center justify-between mb-1">
                <p className="text-xs text-gray-600">Subscription</p>
                <button
                  onClick={handleChangeSubscription}
                  className="text-xs text-purple-600 hover:text-purple-700"
                >
                  {showSubscriptions ? 'Hide' : 'Change'}
                </button>
              </div>
              <p className="text-sm font-medium text-gray-800">
                {currentSubscription.name}
              </p>
              <p className="text-xs text-gray-500 mt-0.5">
                {currentSubscription.state}
              </p>
            </div>
          ) : (
            <div>
              <p className="text-xs text-gray-600 mb-1">Subscription</p>
              <p className="text-xs text-yellow-600">No subscription selected</p>
            </div>
          )}

          {showSubscriptions && subscriptions.length > 0 && (
            <div className="mt-3 border-t border-gray-200 pt-3">
              <p className="text-xs font-medium text-gray-700 mb-2">Select Subscription:</p>
              <div className="max-h-48 overflow-y-auto space-y-1">
                {subscriptions.map((sub) => (
                  <button
                    key={sub.id}
                    onClick={() => handleSetSubscription(sub.id)}
                    disabled={selectingSubscription || sub.id === currentSubscription?.id}
                    className={`w-full text-left px-2 py-1.5 rounded text-xs transition-colors ${
                      sub.id === currentSubscription?.id
                        ? 'bg-purple-100 text-purple-700 border border-purple-300'
                        : 'bg-gray-50 text-gray-700 hover:bg-gray-100 border border-transparent'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{sub.name}</span>
                      {sub.isDefault && (
                        <span className="text-xs text-gray-500">(Default)</span>
                      )}
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      {sub.state} • {sub.id.substring(0, 8)}...
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {showSubscriptions && subscriptions.length === 0 && (
            <div className="mt-3 border-t border-gray-200 pt-3">
              <p className="text-xs text-gray-500">No subscriptions available</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
