<?php
/**
 * A dependency-free SMM Panel API client (v1 and v2).
 *
 * Most panels are PHP, so this is the client most integrators actually paste in.
 *
 *   $p = new SmmPanel('https://panel.example', 'YOUR_KEY');
 *   foreach ($p->services() as $s) { echo $s['name'], ' ', $s['rate'], PHP_EOL; }
 *
 * Choices worth knowing:
 *  - money stays a string; casting "1.02" to float loses cents over a thousand orders
 *  - the {"error": ...} envelope throws instead of returning, because an error that
 *    looks like data is how balances get lost
 */
class SmmPanel
{
    private string $base;
    private string $key;
    private string $version;
    private int $timeout;

    public function __construct(string $baseUrl, string $key, string $version = 'v1', int $timeout = 30)
    {
        $this->base = rtrim($baseUrl, '/');
        $this->key = $key;
        $this->version = $version;
        $this->timeout = $timeout;
    }

    private function call(string $action, array $params = [])
    {
        $query = http_build_query(array_merge(['key' => $this->key, 'action' => $action], $params));
        $url = "{$this->base}/api/{$this->version}?{$query}";

        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT        => $this->timeout,
            CURLOPT_HTTPHEADER     => ['Accept: application/json'],
            CURLOPT_USERAGENT      => 'smm-panel-client/1.0',
        ]);
        $body = curl_exec($ch);
        if ($body === false) {
            $err = curl_error($ch);
            curl_close($ch);
            throw new RuntimeException("transport: {$err}");
        }
        curl_close($ch);

        $data = json_decode($body, true);
        if (!is_array($data)) {
            throw new RuntimeException('response was not JSON: ' . substr($body, 0, 120));
        }
        if (isset($data['error'])) {
            throw new RuntimeException($data['error']);
        }
        return $data;
    }

    public function services(): array { return $this->call('services'); }

    public function balance(): array { return $this->call('balance'); }

    public function status($order): array { return $this->call('status', ['order' => $order]); }

    public function statusMany(array $orders): array
    {
        return $this->call('status', ['orders' => implode(',', $orders)]);
    }

    public function orders(int $limit = 100, int $offset = 0): array
    {
        return $this->call('orders', ['limit' => $limit, 'offset' => $offset])['orders'] ?? [];
    }

    public function add($service, string $link, $quantity, $runs = null, $interval = null): int
    {
        $params = ['service' => $service, 'link' => $link, 'quantity' => $quantity];
        if ($runs !== null)     { $params['runs'] = $runs; }
        if ($interval !== null) { $params['interval'] = $interval; }
        return (int) $this->call('add', $params)['order'];
    }

    public function cancel(array $orders): int
    {
        return (int) $this->call('cancel', ['orders' => implode(',', $orders)])['cancel'];
    }

    public function refill($order): int
    {
        return (int) $this->call('refill', ['order' => $order])['refill'];
    }
}
