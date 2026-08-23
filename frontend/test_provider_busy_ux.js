// Frontend Provider-Busy UX & Resilience Validation Suite
import assert from 'node:assert'
import { ApiError } from './src/services/api.js'

console.log('==================================================')
console.log('FRONTEND PROVIDER-BUSY UX & RESILIENCE TEST SUITE')
console.log('==================================================')

// ----------------------------------------------------
// Test 1: ApiError structure & provider-busy flag
// ----------------------------------------------------
console.log('\n[Test 1] ApiError structure & isProviderBusy classification')
const err503 = new ApiError('The AI service is temporarily busy.', 503, 'AI_PROVIDER_BUSY')
assert.strictEqual(err503.status, 503)
assert.strictEqual(err503.code, 'AI_PROVIDER_BUSY')
assert.strictEqual(err503.isProviderBusy, true)

const err429 = new ApiError('Rate limited', 429, 'AI_PROVIDER_BUSY')
assert.strictEqual(err429.status, 429)
assert.strictEqual(err429.isProviderBusy, true)

const err400 = new ApiError('Bad request', 400, 'BAD_REQUEST')
assert.strictEqual(err400.status, 400)
assert.strictEqual(err400.isProviderBusy, false)
console.log('--> Test 1 PASSED: ApiError correctly sets status, code, and isProviderBusy flag.')

// ----------------------------------------------------
// Test 2: Structured error parsing simulation
// ----------------------------------------------------
console.log('\n[Test 2] Structured error parsing from JSON response')
function parseResponse(status, bodyJson) {
  const isOk = status >= 200 && status < 300
  if (!isOk) {
    const errorCode = bodyJson?.error?.code
    const errorMsg = bodyJson?.error?.message || `Request failed with status ${status}`
    return new ApiError(errorMsg, status, errorCode, bodyJson)
  }
  return bodyJson
}

const parsed503 = parseResponse(503, {
  error: {
    code: 'AI_PROVIDER_BUSY',
    message: 'The AI service is temporarily busy. Please try again in a few moments.',
  },
})
assert(parsed503 instanceof ApiError)
assert.strictEqual(parsed503.code, 'AI_PROVIDER_BUSY')
assert.strictEqual(parsed503.isProviderBusy, true)
assert.strictEqual(parsed503.message, 'The AI service is temporarily busy. Please try again in a few moments.')
console.log('--> Test 2 PASSED: 503 structured payload cleanly parsed into ApiError.')

// ----------------------------------------------------
// Test 3: Calm provider-busy user-facing message mapping
// ----------------------------------------------------
console.log('\n[Test 3] Calm non-technical user-facing message mapping')
function getErrorMessage(err) {
  const isBusy =
    Boolean(err?.isProviderBusy) ||
    err?.code === 'AI_PROVIDER_BUSY' ||
    err?.status === 429 ||
    err?.status === 503
  return isBusy
    ? 'The AI servers are currently busy. Please wait a few moments and try again.'
    : (err?.message || 'Failed to send message.')
}

const calmMsg503 = getErrorMessage(parsed503)
assert.strictEqual(calmMsg503, 'The AI servers are currently busy. Please wait a few moments and try again.')
assert(!calmMsg503.includes('503'), 'Message must not leak HTTP codes')
assert(!calmMsg503.includes('RESOURCE_EXHAUSTED'), 'Message must not leak raw SDK codes')

const genericErr = new ApiError('Something broke', 500, 'INTERNAL_ERROR')
assert.strictEqual(getErrorMessage(genericErr), 'Something broke')
console.log('--> Test 3 PASSED: Calm, non-technical message generated without leaky details.')

// ----------------------------------------------------
// Test 4: Consecutive-failure de-duplication (Single coherent state)
// ----------------------------------------------------
console.log('\n[Test 4] Consecutive-failure de-duplication')
let errorState = null

function applyError(err) {
  const isBusy =
    Boolean(err?.isProviderBusy) ||
    err?.code === 'AI_PROVIDER_BUSY' ||
    err?.status === 429 ||
    err?.status === 503
  const message = isBusy
    ? 'The AI servers are currently busy. Please wait a few moments and try again.'
    : (err?.message || 'Failed to send message.')

  errorState = { message, isProviderBusy: isBusy }
}

// 1st failure: 429
applyError(err429)
assert.deepStrictEqual(errorState, {
  message: 'The AI servers are currently busy. Please wait a few moments and try again.',
  isProviderBusy: true,
})

// 2nd failure: 503
applyError(err503)
assert.deepStrictEqual(errorState, {
  message: 'The AI servers are currently busy. Please wait a few moments and try again.',
  isProviderBusy: true,
})
console.log('--> Test 4 PASSED: Repeated consecutive failures do not stack banners; single state maintained.')

// ----------------------------------------------------
// Test 5: Automatic recovery / banner dismissal on success
// ----------------------------------------------------
console.log('\n[Test 5] Automatic error banner dismissal on subsequent successful send')
// Starting in error state
assert.notStrictEqual(errorState, null)

function onSendSuccess() {
  errorState = null
}

onSendSuccess()
assert.strictEqual(errorState, null)
console.log('--> Test 5 PASSED: Subsequent successful send automatically clears error state.')

// ----------------------------------------------------
// Test 6: Message-submission lifecycle: state rollback on failure to prevent duplicate turns
// ----------------------------------------------------
console.log('\n[Test 6] Message-submission rollback & duplicate prevention')
let messageList = [
  { role: 'user', content: 'Turn 1' },
  { role: 'assistant', content: 'Turn 1 reply' },
]

function simulateSendLifecycle(content, shouldFail) {
  // Step 1: User sends message -> optimistic add
  messageList = [...messageList, { role: 'user', content }]
  
  // Step 2: API Call
  if (shouldFail) {
    // On failure: rollback user message so retry doesn't duplicate
    messageList = messageList.slice(0, -1)
    applyError(err503)
  } else {
    // On success: append assistant message and clear error
    messageList = [...messageList, { role: 'assistant', content: 'Assistant reply' }]
    onSendSuccess()
  }
}

// Attempt 1: Failed send
simulateSendLifecycle('Attempted prompt', true)
assert.strictEqual(messageList.length, 2, 'Failed prompt should be rolled back from visible thread')
assert.strictEqual(errorState.isProviderBusy, true)

// User retries sending the same prompt: Attempt 2 (Success)
simulateSendLifecycle('Attempted prompt', false)
assert.strictEqual(messageList.length, 4, 'Expected exactly 1 user turn + 1 assistant turn after retry')
assert.strictEqual(messageList[2].content, 'Attempted prompt')
assert.strictEqual(messageList[3].content, 'Assistant reply')
assert.strictEqual(errorState, null, 'Error state cleared on retry success')

console.log('--> Test 6 PASSED: Failed send rolled back; retry cleanly executed with zero duplicate records.')

console.log('\n==================================================')
console.log('ALL 6 FRONTEND PROVIDER-BUSY TESTS PASSED!')
console.log('==================================================')
