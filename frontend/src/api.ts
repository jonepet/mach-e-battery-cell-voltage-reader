export function eventsUrl(): string {
  const url = new URL('api/events', window.location.href);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  return url.href;
}

async function request(method: string, path: string, body?: unknown): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`api/${path}`, {
      method,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    throw new Error('The reader service is unreachable.', { cause: error });
  }
  if (!response.ok) {
    throw new Error('The request was rejected. Refresh the port list and try again.');
  }
  return response;
}

export async function listPorts(): Promise<string[]> {
  const response = await request('GET', 'ports');
  return (await response.json()) as string[];
}

export async function connectPort(port: string): Promise<void> {
  await request('PUT', 'connection', { port });
}

export async function disconnectPort(): Promise<void> {
  await request('DELETE', 'connection');
}
