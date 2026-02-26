async function parseResponse(response) {
  const data = await response.json();
  if (!response.ok || data.error) {
    const errorMessage = data.error || "Unexpected API error";
    const error = new Error(errorMessage);
    error.details = data.details || [];
    throw error;
  }
  return data;
}

export async function getContacts(query = "") {
  const queryString = query.trim()
    ? `?query=${encodeURIComponent(query.trim())}`
    : "";
  const response = await fetch(`/contacts/search${queryString}`);
  return parseResponse(response);
}

export async function createContact(payload) {
  const response = await fetch("/contacts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  return parseResponse(response);
}

export async function updateContact(contactId, payload) {
  const response = await fetch(`/contacts/${contactId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  return parseResponse(response);
}

export async function deleteContact(contactId) {
  const response = await fetch(`/contacts/${contactId}`, {
    method: "DELETE"
  });
  return parseResponse(response);
}
