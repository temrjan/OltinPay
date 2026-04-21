/**
 * Non-custodial wallet utilities for OltinPay.
 *
 * Generates a BIP39 seed on the client, encrypts it with the user's PIN
 * (scrypt KDF + AES-256-GCM), and persists the encrypted blob in the
 * Telegram Cloud Storage. The seed never leaves the device unencrypted.
 *
 * KDF choice: scrypt rather than Argon2 — paulmillr's @noble/hashes
 * README explicitly recommends scrypt over Argon2 in JavaScript due to
 * the lack of fast Uint64Array support in the language.
 */

import {generateMnemonic, validateMnemonic} from '@scure/bip39';
import {wordlist} from '@scure/bip39/wordlists/english.js';
import {scryptAsync} from '@noble/hashes/scrypt.js';
import {bytesToHex, hexToBytes, randomBytes} from '@noble/hashes/utils.js';
import {mnemonicToAccount} from 'viem/accounts';
import type {HDAccount} from 'viem/accounts';

const STORAGE_KEY = 'encrypted_wallet_v1';
const SCRYPT_PARAMS = {N: 2 ** 17, r: 8, p: 1, dkLen: 32} as const;
const SALT_LENGTH = 16;
const NONCE_LENGTH = 12;
const HD_PATH = "m/44'/60'/0'/0/0";

export interface EncryptedWallet {
  v: 1;
  salt: string;     // hex
  nonce: string;    // hex (AES-GCM IV)
  ciphertext: string; // hex (encrypted mnemonic + auth tag)
}

// ═══════════════════════════════════════════════════════════════════
// Mnemonic generation & validation
// ═══════════════════════════════════════════════════════════════════

export function newMnemonic(): string {
  return generateMnemonic(wordlist, 128); // 12 words
}

export function isValidMnemonic(phrase: string): boolean {
  return validateMnemonic(phrase.trim().toLowerCase(), wordlist);
}

export function mnemonicToAddress(mnemonic: string): `0x${string}` {
  const account = mnemonicToAccount(mnemonic, {path: HD_PATH});
  return account.address;
}

export function mnemonicToHDAccount(mnemonic: string): HDAccount {
  return mnemonicToAccount(mnemonic, {path: HD_PATH});
}

// ═══════════════════════════════════════════════════════════════════
// Encryption (scrypt + AES-256-GCM via WebCrypto)
// ═══════════════════════════════════════════════════════════════════

async function deriveKey(pin: string, salt: Uint8Array): Promise<CryptoKey> {
  const pinBytes = new TextEncoder().encode(pin);
  const rawKey = await scryptAsync(pinBytes, salt, SCRYPT_PARAMS);
  return crypto.subtle.importKey(
    'raw',
    rawKey,
    {name: 'AES-GCM'},
    false,
    ['encrypt', 'decrypt'],
  );
}

export async function encryptMnemonic(mnemonic: string, pin: string): Promise<EncryptedWallet> {
  if (!isValidMnemonic(mnemonic)) {
    throw new Error('Invalid mnemonic');
  }
  if (pin.length < 4) {
    throw new Error('PIN must be at least 4 characters');
  }
  const salt = randomBytes(SALT_LENGTH);
  const nonce = randomBytes(NONCE_LENGTH);
  const key = await deriveKey(pin, salt);
  const plaintext = new TextEncoder().encode(mnemonic.trim());
  const ciphertextBuffer = await crypto.subtle.encrypt(
    {name: 'AES-GCM', iv: nonce},
    key,
    plaintext,
  );
  return {
    v: 1,
    salt: bytesToHex(salt),
    nonce: bytesToHex(nonce),
    ciphertext: bytesToHex(new Uint8Array(ciphertextBuffer)),
  };
}

export async function decryptMnemonic(
  blob: EncryptedWallet,
  pin: string,
): Promise<string> {
  if (blob.v !== 1) {
    throw new Error(`Unsupported wallet format version: ${blob.v}`);
  }
  const salt = hexToBytes(blob.salt);
  const nonce = hexToBytes(blob.nonce);
  const ciphertext = hexToBytes(blob.ciphertext);
  const key = await deriveKey(pin, salt);
  let plaintext: ArrayBuffer;
  try {
    plaintext = await crypto.subtle.decrypt(
      {name: 'AES-GCM', iv: nonce},
      key,
      ciphertext,
    );
  } catch {
    throw new Error('Invalid PIN');
  }
  const mnemonic = new TextDecoder().decode(plaintext);
  if (!isValidMnemonic(mnemonic)) {
    throw new Error('Decrypted data is not a valid mnemonic');
  }
  return mnemonic;
}

// ═══════════════════════════════════════════════════════════════════
// Telegram Cloud Storage persistence
// ═══════════════════════════════════════════════════════════════════

interface CloudStorage {
  setItem(key: string, value: string, callback?: (err: Error | null, ok?: boolean) => void): void;
  getItem(key: string, callback: (err: Error | null, value?: string) => void): void;
  removeItem(key: string, callback?: (err: Error | null, ok?: boolean) => void): void;
}

function getCloudStorage(): CloudStorage | null {
  if (typeof window === 'undefined') return null;
  const tg = (window as unknown as {Telegram?: {WebApp?: {CloudStorage?: CloudStorage}}}).Telegram?.WebApp;
  return tg?.CloudStorage ?? null;
}

export async function saveEncryptedWallet(blob: EncryptedWallet): Promise<void> {
  const cs = getCloudStorage();
  const json = JSON.stringify(blob);
  if (cs) {
    return new Promise((resolve, reject) => {
      cs.setItem(STORAGE_KEY, json, (err) => {
        if (err) reject(err);
        else resolve();
      });
    });
  }
  // Fallback for browsers outside Telegram
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, json);
    return;
  }
  throw new Error('No storage backend available');
}

export async function loadEncryptedWallet(): Promise<EncryptedWallet | null> {
  const cs = getCloudStorage();
  if (cs) {
    return new Promise((resolve, reject) => {
      cs.getItem(STORAGE_KEY, (err, value) => {
        if (err) {
          reject(err);
          return;
        }
        if (!value) {
          resolve(null);
          return;
        }
        try {
          resolve(JSON.parse(value) as EncryptedWallet);
        } catch {
          resolve(null);
        }
      });
    });
  }
  if (typeof localStorage !== 'undefined') {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as EncryptedWallet;
    } catch {
      return null;
    }
  }
  return null;
}

export async function removeEncryptedWallet(): Promise<void> {
  const cs = getCloudStorage();
  if (cs) {
    return new Promise((resolve, reject) => {
      cs.removeItem(STORAGE_KEY, (err) => {
        if (err) reject(err);
        else resolve();
      });
    });
  }
  if (typeof localStorage !== 'undefined') {
    localStorage.removeItem(STORAGE_KEY);
  }
}

export async function hasWallet(): Promise<boolean> {
  return (await loadEncryptedWallet()) !== null;
}
