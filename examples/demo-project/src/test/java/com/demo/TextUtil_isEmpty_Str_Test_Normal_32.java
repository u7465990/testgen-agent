package com.demo;

import static org.junit.Assert.*;
import org.junit.Test;
import com.demo.TextUtil;

public class TextUtil_isEmpty_Str_Test_Normal_32 {


    @Test
    public void testIsEmptyWithTypicalValues() {
        assertFalse(TextUtil.isEmpty("test"));
        assertTrue(TextUtil.isEmpty(""));
    }

}
