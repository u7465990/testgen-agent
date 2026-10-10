package com.demo;

import com.demo.TextUtil;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class TextUtil_truncate_Str_int_Test_Normal_34 {


    @Test
    public void testTruncateWithRepresentativeValidInputs() {
        // Short string that fits within maxLength is returned unchanged
        Assertions.assertEquals("test", TextUtil.truncate("test", 4));

        // maxLength larger than string length returns the original string
        Assertions.assertEquals("test", TextUtil.truncate("test", 10));

        // maxLength of 1 truncates to first char plus ellipsis
        Assertions.assertEquals("t...", TextUtil.truncate("test", 1));

        // maxLength of 0 on a non-empty string yields just the ellipsis
        Assertions.assertEquals("...", TextUtil.truncate("test", 0));

        // Empty string with maxLength 0 is returned unchanged
        Assertions.assertEquals("", TextUtil.truncate("", 0));

        // Empty string with maxLength 1 is returned unchanged
        Assertions.assertEquals("", TextUtil.truncate("", 1));

        // null string returns null
        Assertions.assertNull(TextUtil.truncate(null, 5));
    }

}
