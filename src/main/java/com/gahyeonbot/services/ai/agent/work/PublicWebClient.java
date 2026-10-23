package com.gahyeonbot.services.ai.agent.work;

import org.apache.http.client.config.RequestConfig;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.impl.client.HttpClients;
import org.apache.http.impl.conn.PoolingHttpClientConnectionManager;
import org.apache.http.conn.socket.ConnectionSocketFactory;
import org.apache.http.conn.socket.PlainConnectionSocketFactory;
import org.apache.http.conn.ssl.SSLConnectionSocketFactory;
import org.apache.http.config.RegistryBuilder;
import java.net.*;
import java.nio.charset.StandardCharsets;

/** Public HTTPS only; pin the checked DNS answer for the connection. No redirects or ambient cookies. */
public final class PublicWebClient {
    public record Page(String url, String contentType, String body) {}
    static URI validateUrl(String url) {
        URI uri = URI.create(url);
        if (!"https".equalsIgnoreCase(uri.getScheme()) || uri.getHost() == null
                || uri.getUserInfo() != null || uri.getFragment() != null
                || uri.getPort() != -1 && uri.getPort() != 443 || url.length() > 2048)
            throw new IllegalArgumentException("Public HTTPS URL required");
        return uri;
    }
    static boolean publicAddress(InetAddress address) {
        byte[] b = address.getAddress();
        if (address.isAnyLocalAddress() || address.isLoopbackAddress() || address.isLinkLocalAddress()
                || address.isSiteLocalAddress() || address.isMulticastAddress()) return false;
        if (b.length != 4) return false; // IPv6, mapped/NAT64 and transition routes fail closed in v1.
        int a = b[0] & 255, c = b[1] & 255;
        return a != 0 && a != 10 && a != 127 && a < 224
                && !(a == 100 && c >= 64 && c <= 127)
                && !(a == 169 && c == 254) && !(a == 172 && c >= 16 && c <= 31)
                && !(a == 192 && (c == 168 || c == 0 || c == 2))
                && !(a == 198 && (c == 18 || c == 19 || c == 51))
                && !(a == 203 && c == 0);
    }
    private static final java.util.Timer DEADLINES = new java.util.Timer("public-web-deadlines", true);
    public Page get(String url) { return fetch(url, 0); }
    private Page fetch(String url, int redirects) {
        if (redirects > 3) throw new IllegalStateException("Redirect limit exceeded");
        URI uri = validateUrl(url);
        try {
            InetAddress[] resolved = InetAddress.getAllByName(uri.getHost());
            var addresses = java.util.Arrays.stream(resolved).filter(PublicWebClient::publicAddress).toArray(InetAddress[]::new);
            // Reject mixed public/private responses too; IPv6 answers are ignored, never connected.
            if (addresses.length == 0 || java.util.Arrays.stream(resolved)
                    .anyMatch(a -> a.getAddress().length == 4 && !publicAddress(a)))
                throw new SecurityException("Non-public destination");
            var sockets = RegistryBuilder.<ConnectionSocketFactory>create()
                    .register("http", PlainConnectionSocketFactory.getSocketFactory())
                    .register("https", SSLConnectionSocketFactory.getSocketFactory()).build();
            var pool = new PoolingHttpClientConnectionManager(sockets, host -> {
                if (!host.equalsIgnoreCase(uri.getHost())) throw new UnknownHostException("Destination changed");
                return addresses;
            });
            try (var client = HttpClients.custom().setConnectionManager(pool).disableRedirectHandling()
                    .disableCookieManagement().disableAutomaticRetries()
                    .setDefaultRequestConfig(RequestConfig.custom().setConnectTimeout(6000)
                            .setSocketTimeout(8000).setConnectionRequestTimeout(6000).build()).build()) {
                var get = new HttpGet(uri);
                get.setHeader("User-Agent", "GahyeonResearch/1.0");
                get.setHeader("Accept", "text/html,application/xhtml+xml,application/rss+xml,application/xml,text/plain");
                var deadline = new java.util.TimerTask() { public void run() { get.abort(); } };
                DEADLINES.schedule(deadline, 12000);
                try (var response = client.execute(get)) {
                    int status = response.getStatusLine().getStatusCode();
                    if (java.util.Set.of(301, 302, 303, 307, 308).contains(status)) {
                        var location = response.getFirstHeader("Location");
                        if (location == null) throw new IllegalStateException("Redirect without destination");
                        String next = uri.resolve(location.getValue()).toString();
                        validateUrl(next);
                        // A fresh connection rechecks DNS and certificate for every hop.
                        return fetch(next, redirects + 1);
                    }
                    if (response.getStatusLine().getStatusCode() != 200 || response.getEntity() == null)
                        throw new IllegalStateException("Source unavailable");
                    String type = response.getEntity().getContentType() == null ? "" : response.getEntity().getContentType().getValue();
                    if (!(type.contains("text/") || type.contains("xml"))) throw new IllegalStateException("Unsupported source type");
                    try (var stream = response.getEntity().getContent()) {
                        byte[] bytes = stream.readNBytes(524289);
                        if (bytes.length > 524288) throw new IllegalStateException("Source exceeds size limit");
                        return new Page(url, type, new String(bytes, StandardCharsets.UTF_8));
                    }
                } finally { deadline.cancel(); DEADLINES.purge(); }
            }
        } catch (java.io.IOException e) { throw new IllegalStateException("Public source fetch failed"); }
    }
}
