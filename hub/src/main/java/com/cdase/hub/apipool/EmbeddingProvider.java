package com.cdase.hub.apipool;

public interface EmbeddingProvider {

    String BGE_QUERY_PREFIX =
            "Represent this sentence for searching relevant passages: ";

    float[] embed(String text) throws Exception;

    default float[] embedDocument(String text) throws Exception {
        return embed(text);
    }

    default float[] embedQuery(String text) throws Exception {
        return embed(BGE_QUERY_PREFIX + text);
    }

    String model();

    int dimensions();

    default boolean available() {
        return true;
    }
}
