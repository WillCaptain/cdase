package com.cdase.hub.apipool;

public final class DisabledEmbeddingProvider implements EmbeddingProvider {

    @Override
    public float[] embed(String text) {
        return null;
    }

    @Override
    public String model() {
        return "disabled";
    }

    @Override
    public int dimensions() {
        return HttpBgeEmbeddingProvider.DEFAULT_DIMENSIONS;
    }

    @Override
    public boolean available() {
        return false;
    }
}
