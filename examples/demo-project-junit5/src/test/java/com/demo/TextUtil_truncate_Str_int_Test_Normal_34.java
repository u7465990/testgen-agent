package com.demo;

import com.demo.TextUtil;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

public class TextUtil_truncate_Str_int_Test_Normal_34 {


    @Test
    public void testTruncateWithRepresentativeValidInputs() {
        // Empty string with maxLength 0: length 0 <= 0, returns as-is
        assertEquals("", TextUtil.truncate("", 0));

        // Non-empty string with maxLength 0: truncated to "" + "..."
        assertEquals("...", TextUtil.truncate("test", 0));

        // Non-empty string with maxLength 1: truncated to "t" + "..."
        assertEquals("t...", TextUtil.truncate("test", 1));

        // String shorter than maxLength: returned unchanged
        assertEquals("test", TextUtil.truncate("test", 10));

        // String exactly equal to maxLength: returned unchanged
        assertEquals("test", TextUtil.truncate("test", 4));

        // Null input returns null
        assertNull(TextUtil.truncate(null, 5));
    }

}
