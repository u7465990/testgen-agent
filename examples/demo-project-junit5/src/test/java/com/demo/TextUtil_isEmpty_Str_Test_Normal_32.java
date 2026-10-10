package com.demo;

import com.demo.TextUtil;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

public class TextUtil_isEmpty_Str_Test_Normal_32 {


    @Test
    public void testIsEmptyWithNormalInputs() {
        // Representative non-empty input should not be considered empty
        assertFalse(TextUtil.isEmpty("test"));

        // Representative empty input should be considered empty
        assertTrue(TextUtil.isEmpty(""));
    }

}
