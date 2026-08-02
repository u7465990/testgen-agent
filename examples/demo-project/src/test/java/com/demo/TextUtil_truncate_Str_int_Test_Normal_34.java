package com.demo;

import org.junit.Test;
import static org.junit.Assert.*;

public class TextUtil_truncate_Str_int_Test_Normal_34 {


    @Test
    public void truncateWithTypicalValues() {
        assertEquals("...", TextUtil.truncate("test", 0));
        assertEquals("t...", TextUtil.truncate("test", 1));
        assertEquals("test", TextUtil.truncate("test", 4));
        assertEquals("", TextUtil.truncate("", 0));
        assertEquals("", TextUtil.truncate("", 1));

        try {
            TextUtil.truncate("test", -1);
            fail("Expected IllegalArgumentException for negative maxLength");
        } catch (IllegalArgumentException expected) {
        }
    }

}
