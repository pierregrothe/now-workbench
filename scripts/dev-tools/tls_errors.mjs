// scripts/dev-tools/tls_errors.mjs
// Names a TLS certificate failure when a capture or playbook cannot load an instance page.
// Author: Pierre Grothe
// Date: 2026-11-07
//
// The drivers verify certificates (STORY-057): a forged or intercepted instance must not feed
// pages into proofs or receive the instance password. Chromium then refuses the page with a
// net::ERR_CERT_* or net::ERR_SSL_* error; this turns it into a sentence a person can act on.

const TLS_ERROR = /net::(ERR_CERT_[A-Z_]+|ERR_SSL_[A-Z_]+|ERR_BAD_SSL_CLIENT_AUTH_CERT)/;

/**
 * Describe why a page could not be loaded.
 * @param {unknown} err The error page.goto threw.
 * @returns {string} The TLS explanation, or the original message.
 */
export function describeLoadError(err) {
  const message = err instanceof Error ? err.message : String(err);
  const tls = TLS_ERROR.exec(message);
  if (tls) {
    return (
      `The instance's TLS certificate was refused (${tls[1]}); nothing was captured. ` +
      "Check the instance URL, or fix the certificate."
    );
  }
  return message;
}
